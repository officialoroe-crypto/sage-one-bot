from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session as DBSession

from workflows.models import Asset, AssetRelation, Project, Workflow, Workspace


class WorkflowRepository:
    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _json(value: Any) -> str | None:
        if value is None:
            return None
        return json.dumps(value, ensure_ascii=False, default=str)

    @staticmethod
    def _load(value: str | None, fallback: Any) -> Any:
        if not value:
            return fallback
        try:
            return json.loads(value)
        except Exception:
            return fallback

    def create_workspace(self, db: DBSession, profile_id: str, name: str, slug: str, workspace_type: str, metadata: dict[str, Any] | None = None) -> Workspace:
        workspace = Workspace(
            id=str(uuid.uuid4()),
            profile_id=profile_id,
            name=name.strip(),
            slug=slug.strip().lower(),
            workspace_type=workspace_type.strip() or "personal",
            metadata_json=self._json(metadata),
            created_at=self._now(),
            updated_at=self._now(),
        )
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
        return workspace

    def get_workspace(self, db: DBSession, profile_id: str, workspace_id: str) -> Workspace | None:
        return db.query(Workspace).filter(Workspace.id == workspace_id, Workspace.profile_id == profile_id).first()

    def list_workspaces(self, db: DBSession, profile_id: str) -> list[Workspace]:
        return db.query(Workspace).filter(Workspace.profile_id == profile_id).order_by(Workspace.created_at.asc()).all()

    def create_project(self, db: DBSession, workspace: Workspace, name: str, project_type: str, description: str | None = None, metadata: dict[str, Any] | None = None) -> Project:
        project = Project(
            id=str(uuid.uuid4()),
            workspace_id=workspace.id,
            name=name.strip(),
            project_type=project_type.strip() or "general",
            status="active",
            description=description,
            metadata_json=self._json(metadata),
            created_at=self._now(),
            updated_at=self._now(),
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return project

    def get_project(self, db: DBSession, profile_id: str, project_id: str) -> Project | None:
        return (
            db.query(Project)
            .join(Workspace, Workspace.id == Project.workspace_id)
            .filter(Project.id == project_id, Workspace.profile_id == profile_id)
            .first()
        )

    def list_projects(self, db: DBSession, profile_id: str, workspace_id: str | None = None) -> list[Project]:
        query = db.query(Project).join(Workspace, Workspace.id == Project.workspace_id).filter(Workspace.profile_id == profile_id)
        if workspace_id:
            query = query.filter(Project.workspace_id == workspace_id)
        return query.order_by(Project.created_at.desc()).all()

    def create_asset(self, db: DBSession, project: Project, name: str, asset_type: str, parent_asset_id: str | None = None, status: str = "draft", path: str | None = None, uri: str | None = None, mime_type: str | None = None, checksum: str | None = None, metadata: dict[str, Any] | None = None) -> Asset:
        asset = Asset(
            id=str(uuid.uuid4()),
            project_id=project.id,
            parent_asset_id=parent_asset_id,
            name=name.strip(),
            asset_type=asset_type.strip(),
            status=status.strip() or "draft",
            path=path,
            uri=uri,
            mime_type=mime_type,
            checksum=checksum,
            metadata_json=self._json(metadata),
            created_at=self._now(),
            updated_at=self._now(),
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset

    def get_asset(self, db: DBSession, profile_id: str, asset_id: str) -> Asset | None:
        return (
            db.query(Asset)
            .join(Project, Project.id == Asset.project_id)
            .join(Workspace, Workspace.id == Project.workspace_id)
            .filter(Asset.id == asset_id, Workspace.profile_id == profile_id)
            .first()
        )

    def list_assets(self, db: DBSession, profile_id: str, project_id: str) -> list[Asset]:
        return (
            db.query(Asset)
            .join(Project, Project.id == Asset.project_id)
            .join(Workspace, Workspace.id == Project.workspace_id)
            .filter(Asset.project_id == project_id, Workspace.profile_id == profile_id)
            .order_by(Asset.created_at.asc())
            .all()
        )

    def create_relation(self, db: DBSession, project: Project, source: Asset, target: Asset, relation_type: str, metadata: dict[str, Any] | None = None) -> AssetRelation:
        if source.project_id != project.id or target.project_id != project.id:
            raise ValueError("Both assets must belong to the selected project.")
        if source.id == target.id:
            raise ValueError("An asset cannot relate to itself.")
        relation = AssetRelation(
            id=str(uuid.uuid4()),
            project_id=project.id,
            source_asset_id=source.id,
            target_asset_id=target.id,
            relation_type=relation_type.strip(),
            metadata_json=self._json(metadata),
            created_at=self._now(),
        )
        db.add(relation)
        db.commit()
        db.refresh(relation)
        return relation

    def list_relations(self, db: DBSession, profile_id: str, project_id: str) -> list[AssetRelation]:
        return (
            db.query(AssetRelation)
            .join(Project, Project.id == AssetRelation.project_id)
            .join(Workspace, Workspace.id == Project.workspace_id)
            .filter(AssetRelation.project_id == project_id, Workspace.profile_id == profile_id)
            .order_by(AssetRelation.created_at.asc())
            .all()
        )

    def create_workflow(self, db: DBSession, project: Project, name: str, workflow_type: str, definition: dict[str, Any], current_stage: str | None = None) -> Workflow:
        workflow = Workflow(
            id=str(uuid.uuid4()),
            project_id=project.id,
            name=name.strip(),
            workflow_type=workflow_type.strip() or "content",
            status="draft",
            current_stage=current_stage,
            definition_json=self._json(definition) or "{}",
            created_at=self._now(),
            updated_at=self._now(),
        )
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        return workflow

    def list_workflows(self, db: DBSession, profile_id: str, project_id: str) -> list[Workflow]:
        return (
            db.query(Workflow)
            .join(Project, Project.id == Workflow.project_id)
            .join(Workspace, Workspace.id == Project.workspace_id)
            .filter(Workflow.project_id == project_id, Workspace.profile_id == profile_id)
            .order_by(Workflow.created_at.desc())
            .all()
        )

    def serialize(self, item: Any) -> dict[str, Any]:
        data = {key: value for key, value in item.__dict__.items() if key != "_sa_instance_state"}
        if "metadata_json" in data:
            data["metadata"] = self._load(data.pop("metadata_json"), {})
        if "definition_json" in data:
            data["definition"] = self._load(data.pop("definition_json"), {})
        for key, value in list(data.items()):
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data


repository = WorkflowRepository()
