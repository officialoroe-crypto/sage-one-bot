"""Durable automation definitions and dispatch into the normal task engine."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from database.connection import SessionLocal
from database.models import Automation


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AutomationService:
    def create(
        self,
        *,
        owner_key: str,
        name: str,
        goal: str,
        schedule_type: str = "once",
        run_at: datetime | None = None,
        interval_seconds: int | None = None,
        session_id: str | None = None,
        agent: str = "general",
        max_runs: int | None = None,
    ) -> dict:
        if not owner_key:
            raise ValueError("owner_key is required.")
        if not name.strip() or not goal.strip():
            raise ValueError("name and goal are required.")
        if schedule_type not in {"once", "interval"}:
            raise ValueError("schedule_type must be 'once' or 'interval'.")
        if schedule_type == "interval":
            if interval_seconds is None or interval_seconds < 60:
                raise ValueError("interval_seconds must be at least 60.")
        if schedule_type == "once" and run_at is None:
            raise ValueError("run_at is required for one-time automations.")
        if max_runs is not None and max_runs < 1:
            raise ValueError("max_runs must be positive.")

        now = _now()
        first_run = run_at or now
        automation = Automation(
            id=str(uuid4()),
            owner_key=owner_key,
            name=name.strip(),
            goal=goal.strip(),
            session_id=session_id,
            agent=agent,
            schedule_type=schedule_type,
            run_at=run_at,
            interval_seconds=interval_seconds,
            next_run_at=first_run,
            max_runs=max_runs,
            enabled=1,
            status="active",
            created_at=now,
            updated_at=now,
        )

        with SessionLocal() as db:
            db.add(automation)
            db.commit()
            db.refresh(automation)
            return self._serialize(automation)

    def list(
        self,
        *,
        owner_key: str,
        enabled_only: bool = False,
        limit: int = 100,
    ) -> list[dict]:
        limit = max(1, min(int(limit), 500))
        with SessionLocal() as db:
            query = db.query(Automation).filter(
                Automation.owner_key == owner_key
            )
            if enabled_only:
                query = query.filter(Automation.enabled == 1)
            rows = query.order_by(
                Automation.created_at.desc()
            ).limit(limit).all()
            return [self._serialize(row) for row in rows]

    def disable(self, *, owner_key: str, automation_id: str) -> dict | None:
        with SessionLocal() as db:
            row = (
                db.query(Automation)
                .filter(
                    Automation.id == automation_id,
                    Automation.owner_key == owner_key,
                )
                .first()
            )
            if row is None:
                return None
            row.enabled = 0
            row.status = "disabled"
            row.updated_at = _now()
            db.commit()
            db.refresh(row)
            return self._serialize(row)

    def dispatch_due(self, *, limit: int = 10) -> list[dict]:
        now = _now()
        limit = max(1, min(int(limit), 50))
        dispatched = []

        with SessionLocal() as db:
            rows = (
                db.query(Automation)
                .filter(
                    Automation.enabled == 1,
                    Automation.status == "active",
                    Automation.next_run_at.is_not(None),
                    Automation.next_run_at <= now,
                )
                .order_by(Automation.next_run_at.asc())
                .limit(limit)
                .all()
            )

            from tasks.engine import tasks

            for row in rows:
                if row.max_runs is not None and row.run_count >= row.max_runs:
                    row.enabled = 0
                    row.status = "completed"
                    row.next_run_at = None
                    row.updated_at = now
                    continue

                task = tasks.create(
                    title=row.name[:120],
                    description=row.goal,
                    priority=3,
                    agent=row.agent,
                    session_id=row.session_id,
                    owner_key=row.owner_key,
                )

                row.last_run_at = now
                row.run_count += 1
                row.last_task_id = task["id"]

                if row.schedule_type == "interval" and row.interval_seconds:
                    row.next_run_at = now + timedelta(seconds=row.interval_seconds)
                else:
                    row.next_run_at = None
                    row.enabled = 0
                    row.status = "completed"

                row.updated_at = now
                try:
                    from events.service import event_store

                    event_store.emit(
                        event_type="AutomationTriggered",
                        task_id=task["id"],
                        session_id=row.session_id,
                        status="dispatched",
                        source="automation",
                        payload={
                            "automation_id": row.id,
                            "name": row.name,
                            "run_count": row.run_count,
                        },
                    )
                except Exception:
                    pass

                dispatched.append({
                    "automation_id": row.id,
                    "task": task,
                    "next_run_at": (
                        row.next_run_at.isoformat()
                        if row.next_run_at else None
                    ),
                })

            db.commit()

        return dispatched

    @staticmethod
    def _serialize(row: Automation) -> dict:
        return {
            "id": row.id,
            "owner_key": row.owner_key,
            "name": row.name,
            "goal": row.goal,
            "session_id": row.session_id,
            "agent": row.agent,
            "schedule_type": row.schedule_type,
            "run_at": row.run_at.isoformat() if row.run_at else None,
            "interval_seconds": row.interval_seconds,
            "next_run_at": row.next_run_at.isoformat() if row.next_run_at else None,
            "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
            "run_count": row.run_count,
            "max_runs": row.max_runs,
            "enabled": bool(row.enabled),
            "status": row.status,
            "last_task_id": row.last_task_id,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }


automation = AutomationService()
