from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from database.connection import SessionLocal
from identity.auth import authenticate_request, get_or_create_authenticated_profile
from workflows import repository

router = APIRouter(prefix="/workflow", tags=["workflow"])


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
    workspace_type: str = Field(default="personal", min_length=1, max_length=50)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    project_type: str = Field(default="general", min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=20000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssetCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    asset_type: str = Field(min_length=1, max_length=80)
    parent_asset_id: str | None = None
    status: str = Field(default="draft", min_length=1, max_length=50)
    path: str | None = None
    uri: str | None = None
    mime_type: str | None = None
    checksum: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RelationCreateRequest(BaseModel):
    source_asset_id: str
    target_asset_id: str
    relation_type: str = Field(min_length=1, max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    workflow_type: str = Field(default="content", min_length=1, max_length=80)
    current_stage: str | None = Field(default=None, max_length=100)
    definition: dict[str, Any] = Field(default_factory=dict)


def _profile_id(claims: dict[str, Any]) -> str:
    return get_or_create_authenticated_profile(claims)["id"]


def _serialize_many(items: list[Any]) -> list[dict[str, Any]]:
    return [repository.serialize(item) for item in items]


@router.get("/workspaces")
def list_workspaces(claims: dict[str, Any] = Depends(authenticate_request)):
    with SessionLocal() as db:
        profile_id = _profile_id(claims)
        return {"success": True, "workspaces": _serialize_many(repository.list_workspaces(db, profile_id))}


@router.post("/workspaces")
def create_workspace(request: WorkspaceCreateRequest, claims: dict[str, Any] = Depends(authenticate_request)):
    with SessionLocal() as db:
        workspace = repository.create_workspace(
            db,
            _profile_id(claims),
            request.name,
            request.slug,
            request.workspace_type,
            request.metadata,
        )
        return {"success": True, "workspace": repository.serialize(workspace)}


@router.get("/workspaces/{workspace_id}/projects")
def list_projects(workspace_id: str, claims: dict[str, Any] = Depends(authenticate_request)):
    with SessionLocal() as db:
        profile_id = _profile_id(claims)
        workspace = repository.get_workspace(db, profile_id, workspace_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        return {"success": True, "projects": _serialize_many(repository.list_projects(db, profile_id, workspace_id))}


@router.post("/workspaces/{workspace_id}/projects")
def create_project(workspace_id: str, request: ProjectCreateRequest, claims: dict[str, Any] = Depends(authenticate_request)):
    with SessionLocal() as db:
        profile_id = _profile_id(claims)
        workspace = repository.get_workspace(db, profile_id, workspace_id)
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        project = repository.create_project(db, workspace, request.name, request.project_type, request.description, request.metadata)
        return {"success": True, "project": repository.serialize(project)}


@router.get("/projects/{project_id}/assets")
def list_assets(project_id: str, claims: dict[str, Any] = Depends(authenticate_request)):
    with SessionLocal() as db:
        profile_id = _profile_id(claims)
        project = repository.get_project(db, profile_id, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"success": True, "assets": _serialize_many(repository.list_assets(db, profile_id, project_id))}


@router.post("/projects/{project_id}/assets")
def create_asset(project_id: str, request: AssetCreateRequest, claims: dict[str, Any] = Depends(authenticate_request)):
    with SessionLocal() as db:
        profile_id = _profile_id(claims)
        project = repository.get_project(db, profile_id, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        if request.parent_asset_id:
            parent = repository.get_asset(db, profile_id, request.parent_asset_id)
            if parent is None or parent.project_id != project_id:
                raise HTTPException(status_code=400, detail="Parent asset must belong to the selected project")
        asset = repository.create_asset(
            db,
            project,
            request.name,
            request.asset_type,
            request.parent_asset_id,
            request.status,
            request.path,
            request.uri,
            request.mime_type,
            request.checksum,
            request.metadata,
        )
        return {"success": True, "asset": repository.serialize(asset)}


@router.get("/projects/{project_id}/relations")
def list_relations(project_id: str, claims: dict[str, Any] = Depends(authenticate_request)):
    with SessionLocal() as db:
        profile_id = _profile_id(claims)
        project = repository.get_project(db, profile_id, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"success": True, "relations": _serialize_many(repository.list_relations(db, profile_id, project_id))}


@router.post("/projects/{project_id}/relations")
def create_relation(project_id: str, request: RelationCreateRequest, claims: dict[str, Any] = Depends(authenticate_request)):
    with SessionLocal() as db:
        profile_id = _profile_id(claims)
        project = repository.get_project(db, profile_id, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        source = repository.get_asset(db, profile_id, request.source_asset_id)
        target = repository.get_asset(db, profile_id, request.target_asset_id)
        if source is None or target is None:
            raise HTTPException(status_code=404, detail="Source or target asset not found")
        try:
            relation = repository.create_relation(db, project, source, target, request.relation_type, request.metadata)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"success": True, "relation": repository.serialize(relation)}


@router.get("/projects/{project_id}/workflows")
def list_workflows(project_id: str, claims: dict[str, Any] = Depends(authenticate_request)):
    with SessionLocal() as db:
        profile_id = _profile_id(claims)
        project = repository.get_project(db, profile_id, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"success": True, "workflows": _serialize_many(repository.list_workflows(db, profile_id, project_id))}


@router.post("/projects/{project_id}/workflows")
def create_workflow(project_id: str, request: WorkflowCreateRequest, claims: dict[str, Any] = Depends(authenticate_request)):
    with SessionLocal() as db:
        profile_id = _profile_id(claims)
        project = repository.get_project(db, profile_id, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        workflow = repository.create_workflow(
            db,
            project,
            request.name,
            request.workflow_type,
            request.definition,
            request.current_stage,
        )
        return {"success": True, "workflow": repository.serialize(workflow)}
