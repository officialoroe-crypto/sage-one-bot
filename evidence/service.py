"""Read-only access to durable action evidence."""

from __future__ import annotations

import json

from sqlalchemy import select

from database.connection import SessionLocal
from database.models import ActionEvidence


class EvidenceService:
    @staticmethod
    def _serialize(row: ActionEvidence) -> dict:
        content = None
        if row.content:
            try:
                content = json.loads(row.content)
            except json.JSONDecodeError:
                content = row.content

        return {
            "id": row.id,
            "action_id": row.action_id,
            "mission_id": row.mission_id,
            "task_id": row.task_id,
            "parent_action_id": row.parent_action_id,
            "evidence_type": row.evidence_type,
            "content": content,
            "verified": bool(row.verified),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    def list(
        self,
        *,
        action_id: str | None = None,
        mission_id: str | None = None,
        task_id: str | None = None,
        evidence_type: str | None = None,
        verified_only: bool = False,
        limit: int = 100,
    ) -> list[dict]:
        limit = max(1, min(int(limit), 500))

        with SessionLocal() as db:
            query = select(ActionEvidence)

            if action_id:
                query = query.where(ActionEvidence.action_id == action_id)
            if mission_id:
                query = query.where(ActionEvidence.mission_id == mission_id)
            if task_id:
                query = query.where(ActionEvidence.task_id == task_id)
            if evidence_type:
                query = query.where(ActionEvidence.evidence_type == evidence_type)
            if verified_only:
                query = query.where(ActionEvidence.verified == 1)

            query = query.order_by(
                ActionEvidence.created_at.asc(),
                ActionEvidence.id.asc(),
            ).limit(limit)

            return [
                self._serialize(row)
                for row in db.scalars(query).all()
            ]


evidence_service = EvidenceService()
