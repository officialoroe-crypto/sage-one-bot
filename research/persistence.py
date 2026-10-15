from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from database.connection import SessionLocal
from database.models import ResearchRecord


class ResearchPersistence:
    """Persist complete research reports without enlarging task rows."""

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def save(
        self,
        report: dict[str, Any],
        *,
        task_id: str | None = None,
        session_id: str | None = None,
        owner_key: str | None = None,
    ) -> dict[str, Any]:
        question = str(report.get("question", "")).strip()
        if not question:
            raise ValueError("Research report question cannot be empty.")

        report_json = json.dumps(
            report,
            ensure_ascii=False,
            default=str,
            separators=(",", ":"),
        )

        db = SessionLocal()
        try:
            record = None
            if task_id:
                record = (
                    db.query(ResearchRecord)
                    .filter(ResearchRecord.task_id == task_id)
                    .filter(ResearchRecord.owner_key == owner_key)
                    .order_by(ResearchRecord.created_at.desc())
                    .first()
                )

            now = self._now()
            if record is None:
                record = ResearchRecord(
                    id=str(uuid.uuid4()),
                    owner_key=owner_key,
                    task_id=task_id,
                    session_id=session_id,
                    question=question,
                    created_at=now,
                )
                db.add(record)

            record.session_id = session_id or record.session_id
            record.question = question
            record.status = "completed" if report.get("success") else "failed"
            record.summary = str(report.get("summary", ""))[:20000] or None
            record.source_count = int(report.get("source_count", 0) or 0)
            record.evidence_count = int(report.get("evidence_count", 0) or 0)
            record.claim_count = int(report.get("claim_count", 0) or 0)
            record.provider = report.get("provider")
            record.model = report.get("model")
            record.report_json = report_json

            db.commit()
            db.refresh(record)

            return {
                "research_id": record.id,
                "task_id": record.task_id,
                "status": record.status,
                "source_count": record.source_count,
                "evidence_count": record.evidence_count,
                "claim_count": record.claim_count,
                "created_at": record.created_at.isoformat(),
            }
        finally:
            db.close()

    def get(self, research_id: str, owner_key: str | None = None) -> dict[str, Any] | None:
        db = SessionLocal()
        try:
            record = (
                db.query(ResearchRecord)
                .filter(ResearchRecord.id == research_id)
                .filter(*([ResearchRecord.owner_key == owner_key] if owner_key is not None else []))
                .first()
            )
            return self._serialize(record) if record else None
        finally:
            db.close()

    def get_by_task(self, task_id: str, owner_key: str | None = None) -> dict[str, Any] | None:
        db = SessionLocal()
        try:
            record = (
                db.query(ResearchRecord)
                .filter(ResearchRecord.task_id == task_id)
                .filter(*([ResearchRecord.owner_key == owner_key] if owner_key is not None else []))
                .order_by(ResearchRecord.created_at.desc())
                .first()
            )
            return self._serialize(record) if record else None
        finally:
            db.close()

    def list(
        self,
        *,
        session_id: str | None = None,
        limit: int = 50,
        owner_key: str | None = None,
    ) -> list[dict[str, Any]]:
        db = SessionLocal()
        try:
            query = db.query(ResearchRecord)
            if owner_key is not None:
                query = query.filter(ResearchRecord.owner_key == owner_key)
            if session_id:
                query = query.filter(ResearchRecord.session_id == session_id)
            records = (
                query
                .order_by(ResearchRecord.created_at.desc())
                .limit(max(1, min(int(limit), 100)))
                .all()
            )
            return [self._serialize(record, include_report=False) for record in records]
        finally:
            db.close()

    @staticmethod
    def _serialize(
        record: ResearchRecord,
        *,
        include_report: bool = True,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "research_id": record.id,
            "task_id": record.task_id,
            "session_id": record.session_id,
            "question": record.question,
            "status": record.status,
            "summary": record.summary,
            "source_count": record.source_count,
            "evidence_count": record.evidence_count,
            "claim_count": record.claim_count,
            "provider": record.provider,
            "model": record.model,
            "created_at": record.created_at.isoformat(),
        }
        if include_report:
            try:
                result["report"] = json.loads(record.report_json)
            except (TypeError, json.JSONDecodeError):
                result["report"] = None
        return result


research_persistence = ResearchPersistence()
