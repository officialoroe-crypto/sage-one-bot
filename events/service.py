from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from uuid import uuid4

from database.connection import SessionLocal
from database.models import ExecutionEvent


class SQLAlchemyEventStore:
    """Persist lifecycle events without owning business state."""

    def emit(
        self,
        *,
        event_type: str,
        action_id: str | None = None,
        session_id: str | None = None,
        mission_id: str | None = None,
        task_id: str | None = None,
        parent_action_id: str | None = None,
        status: str | None = None,
        source: str = "sage",
        payload: Any = None,
        db: Session | None = None,
        commit: bool = True,
    ) -> str | None:
        event_id = str(uuid4())
        owns_session = db is None
        session = db or SessionLocal()
        try:
            bind = getattr(session, "bind", None)
            if bind is not None:
                connection = session.connection()
                if not inspect(connection).has_table("execution_events"):
                    return None

            row = ExecutionEvent(
                id=event_id,
                event_type=event_type,
                action_id=action_id,
                session_id=session_id,
                mission_id=mission_id,
                task_id=task_id,
                parent_action_id=parent_action_id,
                status=status,
                source=source,
                payload=(
                    json.dumps(payload, ensure_ascii=False, default=str)
                    if payload is not None
                    else None
                ),
                created_at=datetime.now(timezone.utc),
            )
            session.add(row)
            if commit:
                session.commit()
            return event_id
        except OperationalError as error:
            session.rollback()
            if "no such table: execution_events" in str(error).lower():
                return None
            raise
        except Exception:
            session.rollback()
            raise
        finally:
            if owns_session:
                session.close()


    @staticmethod
    def _serialize(row: ExecutionEvent) -> dict[str, Any]:
        payload = None
        if row.payload:
            try:
                payload = json.loads(row.payload)
            except json.JSONDecodeError:
                payload = row.payload
        return {
            "id": row.id,
            "event_type": row.event_type,
            "action_id": row.action_id,
            "session_id": row.session_id,
            "mission_id": row.mission_id,
            "task_id": row.task_id,
            "parent_action_id": row.parent_action_id,
            "status": row.status,
            "source": row.source,
            "payload": payload,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    def list(
        self,
        *,
        action_id: str | None = None,
        session_id: str | None = None,
        mission_id: str | None = None,
        task_id: str | None = None,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        db = SessionLocal()
        try:
            query = select(ExecutionEvent)
            if action_id:
                query = query.where(ExecutionEvent.action_id == action_id)
            if session_id:
                query = query.where(ExecutionEvent.session_id == session_id)
            if mission_id:
                query = query.where(ExecutionEvent.mission_id == mission_id)
            if task_id:
                query = query.where(ExecutionEvent.task_id == task_id)
            if event_type:
                query = query.where(ExecutionEvent.event_type == event_type)
            query = query.order_by(
                ExecutionEvent.created_at.asc(),
                ExecutionEvent.id.asc(),
            ).limit(limit)
            return [self._serialize(row) for row in db.scalars(query).all()]
        finally:
            db.close()

event_store = SQLAlchemyEventStore()
