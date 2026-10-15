from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session as DBSession

from database.models import (
    Session,
    Message,
    Memory,
    Task,
    ActionLog,
    Notification,
)


class SageRepository:
    # ============================================================
    # DATETIME HELPERS
    # ============================================================

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _normalize_datetime(
        value: datetime | None,
    ) -> datetime | None:
        """
        Normalize database/application datetimes to UTC-aware
        datetimes before performing arithmetic.

        SQLite may return DateTime values without timezone information
        even when the application originally stored timezone-aware values.
        """

        if value is None:
            return None

        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)

        return value.astimezone(timezone.utc)

    @classmethod
    def _duration_ms(
        cls,
        started_at: datetime | None,
        completed_at: datetime | None,
    ) -> int | None:
        if not started_at or not completed_at:
            return None

        started = cls._normalize_datetime(started_at)
        completed = cls._normalize_datetime(completed_at)

        if started is None or completed is None:
            return None

        delta = completed - started

        return max(
            0,
            int(delta.total_seconds() * 1000),
        )

    # ============================================================
    # SESSIONS
    # ============================================================

    def create_session(
        self,
        db: DBSession,
        profile_id: str | None = None,
        owner_key: str | None = None,
    ) -> str:
        session_id = str(uuid.uuid4())

        session = Session(
            id=session_id,
            profile_id=profile_id,
            owner_key=owner_key,
            created_at=self._utc_now(),
        )

        db.add(session)
        db.commit()

        return session_id

    def get_session(
        self,
        db: DBSession,
        session_id: str,
        owner_key: str | None = None,
    ) -> Session | None:
        query = db.query(Session).filter(Session.id == session_id)
        if owner_key is not None:
            query = query.filter(Session.owner_key == owner_key)
        return query.first()

    # ============================================================
    # MESSAGES
    # ============================================================

    def add_message(
        self,
        db: DBSession,
        session_id: str,
        role: str,
        content: str,
    ) -> Message:
        message = Message(
            session_id=session_id,
            role=role,
            content=content,
            created_at=self._utc_now(),
        )

        db.add(message)
        db.commit()

        return message

    def get_messages(
        self,
        db: DBSession,
        session_id: str,
        limit: int = 10,
    ) -> list[Message]:
        return (
            db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .all()
        )

    # ============================================================
    # MEMORY
    # ============================================================

    def add_memory(
        self,
        db: DBSession,
        content: str,
        memory_type: str = "fact",
        importance: float = 0.5,
        confidence: float = 1.0,
        source: str = "conversation",
        owner_key: str | None = None,
        profile_id: str | None = None,
    ) -> Memory:
        existing = (
            db.query(Memory)
            .filter(Memory.content == content)
            .filter(Memory.owner_key == owner_key)
            .first()
        )

        if existing:
            return existing

        now = self._utc_now()

        memory = Memory(
            id=str(uuid.uuid4()),
            owner_key=owner_key,
            profile_id=profile_id,
            memory_type=memory_type,
            content=content,
            importance=importance,
            confidence=confidence,
            source=source,
            created_at=now,
            updated_at=now,
        )

        db.add(memory)
        db.commit()

        return memory

    def get_memories(
        self,
        db: DBSession,
        limit: int = 20,
        owner_key: str | None = None,
        profile_id: str | None = None,
    ) -> list[Memory]:
        query = db.query(Memory)
        if owner_key is not None:
            query = query.filter(Memory.owner_key == owner_key)
        if profile_id is not None:
            query = query.filter(Memory.profile_id == profile_id)
        return (query
            .order_by(Memory.importance.desc())
            .limit(limit)
            .all()
        )

    # ============================================================
    # TASKS
    # ============================================================

    def create_task(
        self,
        db: DBSession,
        title: str,
        description: str,
        priority: int = 3,
        agent: str = "general",
        session_id: str | None = None,
        parent_task_id: str | None = None,
        max_retries: int = 3,
        profile_id: str | None = None,
        project_id: str | None = None,
        owner_key: str | None = None,
        premium_work_key: str | None = None,
    ) -> Task:
        now = self._utc_now()

        task = Task(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            status="pending",
            priority=priority,
            agent=agent,
            session_id=session_id,
            parent_task_id=parent_task_id,
            profile_id=profile_id,
            project_id=project_id,
            owner_key=owner_key,
            premium_work_key=premium_work_key,
            progress=0,
            retries=0,
            max_retries=max_retries,
            created_at=now,
            updated_at=now,
        )

        db.add(task)
        db.commit()

        return task

    def get_task(
        self,
        db: DBSession,
        task_id: str,
        owner_key: str | None = None,
    ) -> Task | None:
        query = db.query(Task).filter(Task.id == task_id)
        if owner_key is not None:
            query = query.filter(Task.owner_key == owner_key)
        return query.first()

    def get_tasks(
        self,
        db: DBSession,
        status: str | None = None,
        limit: int = 100,
        owner_key: str | None = None,
    ) -> list[Task]:
        query = db.query(Task)

        if status:
            query = query.filter(Task.status == status)
        if owner_key is not None:
            query = query.filter(Task.owner_key == owner_key)

        return (
            query
            .order_by(
                Task.priority.asc(),
                Task.created_at.asc(),
            )
            .limit(limit)
            .all()
        )

    def update_task(
        self,
        db: DBSession,
        task_id: str,
        owner_key: str | None = None,
        **updates: Any,
    ) -> Task | None:
        task = self.get_task(db, task_id, owner_key=owner_key)

        if not task:
            return None

        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)

        task.updated_at = self._utc_now()

        db.commit()

        return task

    # ============================================================
    # DURABLE WORKER / TASK LEASING
    # ============================================================

    def claim_next_task(
        self,
        db: DBSession,
        worker_id: str,
        lease_seconds: int = 120,
    ) -> Task | None:
        """Atomically claim the highest-priority eligible pending task."""

        now = self._utc_now()
        lease_seconds = max(30, int(lease_seconds))
        lease_expires = now.timestamp() + lease_seconds
        lease_time = datetime.fromtimestamp(
            lease_expires,
            tz=timezone.utc,
        )

        candidate = (
            db.query(Task.id)
            .filter(Task.status == 'pending')
            .filter(
                (Task.next_retry_at.is_(None))
                | (Task.next_retry_at <= now)
            )
            .order_by(
                Task.priority.asc(),
                Task.created_at.asc(),
            )
            .first()
        )

        if not candidate:
            return None

        task_id = candidate[0]

        updated = (
            db.query(Task)
            .filter(Task.id == task_id)
            .filter(Task.status == 'pending')
            .filter(
                (Task.next_retry_at.is_(None))
                | (Task.next_retry_at <= now)
            )
            .update(
                {
                    Task.status: 'running',
                    Task.worker_id: worker_id,
                    Task.lease_expires_at: lease_time,
                    Task.heartbeat_at: now,
                    Task.started_at: now,
                    Task.updated_at: now,
                },
                synchronize_session=False,
            )
        )

        if updated != 1:
            db.rollback()
            return None

        db.commit()
        return self.get_task(db, task_id)

    def heartbeat_task(
        self,
        db: DBSession,
        task_id: str,
        worker_id: str,
        lease_seconds: int = 120,
    ) -> Task | None:
        """Refresh a task lease only when this worker owns the task."""

        now = self._utc_now()
        lease_seconds = max(30, int(lease_seconds))
        lease_expires = datetime.fromtimestamp(
            now.timestamp() + lease_seconds,
            tz=timezone.utc,
        )

        updated = (
            db.query(Task)
            .filter(Task.id == task_id)
            .filter(Task.status == 'running')
            .filter(Task.worker_id == worker_id)
            .update(
                {
                    Task.lease_expires_at: lease_expires,
                    Task.heartbeat_at: now,
                    Task.updated_at: now,
                },
                synchronize_session=False,
            )
        )

        if updated != 1:
            db.rollback()
            return None

        db.commit()
        return self.get_task(db, task_id)

    def complete_task_claim(
        self,
        db: DBSession,
        task_id: str,
        worker_id: str,
        result: str,
    ) -> Task | None:
        """Complete a task only when the supplied worker owns its lease."""

        now = self._utc_now()

        updated = (
            db.query(Task)
            .filter(Task.id == task_id)
            .filter(Task.status == 'running')
            .filter(Task.worker_id == worker_id)
            .update(
                {
                    Task.status: 'completed',
                    Task.progress: 100,
                    Task.result: result,
                    Task.error: None,
                    Task.completed_at: now,
                    Task.worker_id: None,
                    Task.lease_expires_at: None,
                    Task.heartbeat_at: None,
                    Task.next_retry_at: None,
                    Task.updated_at: now,
                },
                synchronize_session=False,
            )
        )

        if updated != 1:
            db.rollback()
            return None

        db.commit()
        return self.get_task(db, task_id)

    def fail_task_claim(
        self,
        db: DBSession,
        task_id: str,
        worker_id: str,
        error: str,
        retry_delay_seconds: int = 10,
    ) -> Task | None:
        """Fail/requeue a task only when the supplied worker owns it."""

        task = (
            db.query(Task)
            .filter(Task.id == task_id)
            .filter(Task.status == 'running')
            .filter(Task.worker_id == worker_id)
            .first()
        )

        if not task:
            return None

        now = self._utc_now()
        new_retries = task.retries + 1

        if new_retries < task.max_retries:
            status = 'pending'
            next_retry_at = datetime.fromtimestamp(
                now.timestamp() + max(1, int(retry_delay_seconds)),
                tz=timezone.utc,
            )
        else:
            status = 'failed'
            next_retry_at = None

        task.status = status
        task.retries = new_retries
        task.error = str(error)
        task.worker_id = None
        task.lease_expires_at = None
        task.heartbeat_at = None
        task.next_retry_at = next_retry_at
        task.updated_at = now

        if status == 'failed':
            task.completed_at = now

        db.commit()
        return task

    def recover_expired_tasks(
        self,
        db: DBSession,
    ) -> int:
        """Recover expired leases while respecting the task retry budget."""

        now = self._utc_now()

        expired = (
            db.query(Task)
            .filter(Task.status == 'running')
            .filter(Task.lease_expires_at.is_not(None))
            .filter(Task.lease_expires_at < now)
            .all()
        )

        recovered = 0

        for task in expired:
            task.retries += 1
            task.worker_id = None
            task.lease_expires_at = None
            task.heartbeat_at = None
            task.error = 'Worker lease expired; task ownership was lost.'

            if task.retries >= task.max_retries:
                task.status = 'failed'
                task.next_retry_at = None
                task.completed_at = now
            else:
                task.status = 'pending'
                task.next_retry_at = now

            task.updated_at = now
            recovered += 1

        if recovered:
            db.commit()

        return recovered

    # ============================================================
    # ACTION / EXECUTION LEDGER
    # ============================================================

    def create_action(
        self,
        db: DBSession,
        tool: str,
        permission: str,
        risk: str,
        capability: str | None = None,
        session_id: str | None = None,
        task_id: str | None = None,
        arguments: dict | None = None,
        permission_allowed: bool = False,
        permission_reason: str | None = None,
        owner_key: str | None = None,
    ) -> ActionLog:
        action = ActionLog(
            id=str(uuid.uuid4()),
            owner_key=owner_key,
            session_id=session_id,
            task_id=task_id,
            tool=tool,
            capability=capability,
            permission=permission,
            risk=risk,
            arguments=(
                json.dumps(
                    arguments,
                    default=str,
                )
                if arguments is not None
                else None
            ),
            permission_allowed=(
                1 if permission_allowed else 0
            ),
            permission_reason=permission_reason,
            status=(
                "started"
                if permission_allowed
                else "denied"
            ),
            started_at=self._utc_now(),
        )

        db.add(action)
        db.commit()

        return action

    def complete_action(
        self,
        db: DBSession,
        action_id: str,
        result: Any = None,
    ) -> ActionLog | None:
        action = (
            db.query(ActionLog)
            .filter(ActionLog.id == action_id)
            .first()
        )

        if not action:
            return None

        now = self._utc_now()

        duration_ms = self._duration_ms(
            action.started_at,
            now,
        )

        action.status = "completed"

        action.result = json.dumps(
            result,
            default=str,
        )

        action.error = None
        action.completed_at = now
        action.duration_ms = duration_ms

        db.commit()

        return action

    def fail_action(
        self,
        db: DBSession,
        action_id: str,
        error: str,
    ) -> ActionLog | None:
        action = (
            db.query(ActionLog)
            .filter(ActionLog.id == action_id)
            .first()
        )

        if not action:
            return None

        now = self._utc_now()

        duration_ms = self._duration_ms(
            action.started_at,
            now,
        )

        action.status = "failed"
        action.error = str(error)
        action.completed_at = now
        action.duration_ms = duration_ms

        db.commit()

        return action

    def get_actions(
        self,
        db: DBSession,
        session_id: str | None = None,
        task_id: str | None = None,
        tool: str | None = None,
        status: str | None = None,
        limit: int = 100,
        owner_key: str | None = None,
    ) -> list[ActionLog]:
        query = db.query(ActionLog)

        if owner_key is not None:
            query = query.filter(ActionLog.owner_key == owner_key)

        if session_id:
            query = query.filter(
                ActionLog.session_id == session_id
            )

        if task_id:
            query = query.filter(
                ActionLog.task_id == task_id
            )

        if tool:
            query = query.filter(
                ActionLog.tool == tool
            )

        if status:
            query = query.filter(
                ActionLog.status == status
            )

        return (
            query
            .order_by(ActionLog.started_at.desc())
            .limit(limit)
            .all()
        )


    # ============================================================
    # NOTIFICATIONS
    # ============================================================

    def create_notification(
        self,
        db: DBSession,
        title: str,
        body: str,
        notification_type: str = "task",
        task_id: str | None = None,
        session_id: str | None = None,
        owner_key: str | None = None,
    ) -> Notification:
        notification = Notification(
            id=str(uuid.uuid4()),
            owner_key=owner_key,
            task_id=task_id,
            session_id=session_id,
            notification_type=notification_type,
            title=title,
            body=body,
            created_at=self._utc_now(),
        )
        db.add(notification)
        db.commit()
        return notification

    def get_notifications(
        self,
        db: DBSession,
        session_id: str | None = None,
        unread_only: bool = False,
        limit: int = 50,
        owner_key: str | None = None,
    ) -> list[Notification]:
        query = db.query(Notification)
        if owner_key is not None:
            query = query.filter(Notification.owner_key == owner_key)
        if session_id:
            query = query.filter(Notification.session_id == session_id)
        if unread_only:
            query = query.filter(Notification.read_at.is_(None))
        return (
            query
            .order_by(Notification.created_at.desc())
            .limit(max(1, min(limit, 200)))
            .all()
        )

    def mark_notification_read(
        self,
        db: DBSession,
        notification_id: str,
        owner_key: str | None = None,
    ) -> Notification | None:
        notification = (
            db.query(Notification)
            .filter(Notification.id == notification_id)
            .first()
        )
        if not notification:
            return None
        if notification.read_at is None:
            notification.read_at = self._utc_now()
            db.commit()
        return notification

    def mark_all_notifications_read(
        self,
        db: DBSession,
        session_id: str | None = None,
        owner_key: str | None = None,
    ) -> int:
        query = db.query(Notification).filter(Notification.read_at.is_(None))
        if owner_key is not None:
            query = query.filter(Notification.owner_key == owner_key)
        if session_id:
            query = query.filter(Notification.session_id == session_id)
        notifications = query.all()
        now = self._utc_now()
        for notification in notifications:
            notification.read_at = now
        if notifications:
            db.commit()
        return len(notifications)


# ================================================================
# GLOBAL REPOSITORY INSTANCE
# ================================================================

repository = SageRepository()


# ================================================================
# MODULE-LEVEL COMPATIBILITY FUNCTIONS
#
# main.py and older modules can safely use:
#
#     repository.create_session(...)
#
# while newer code can use:
#
#     repository.repository.create_session(...)
#
# These wrappers intentionally delegate to the single repository
# instance above.
# ================================================================

def create_session(
    db: DBSession,
    profile_id: str | None = None,
    owner_key: str | None = None,
) -> str:
    return repository.create_session(db, profile_id, owner_key)


def get_session(
    db: DBSession,
    session_id: str,
    owner_key: str | None = None,
) -> Session | None:
    return repository.get_session(db, session_id, owner_key)


def add_message(
    db: DBSession,
    session_id: str,
    role: str,
    content: str,
) -> Message:
    return repository.add_message(
        db,
        session_id,
        role,
        content,
    )


def get_messages(
    db: DBSession,
    session_id: str,
    limit: int = 10,
) -> list[Message]:
    return repository.get_messages(
        db,
        session_id,
        limit,
    )


def add_memory(
    db: DBSession,
    content: str,
    memory_type: str = "fact",
    importance: float = 0.5,
    confidence: float = 1.0,
    source: str = "conversation",
    owner_key: str | None = None,
    profile_id: str | None = None,
) -> Memory:
    return repository.add_memory(
        db,
        content,
        memory_type,
        importance,
        confidence,
        source,
        owner_key,
        profile_id,
    )


def get_memories(
    db: DBSession,
    limit: int = 20,
    owner_key: str | None = None,
    profile_id: str | None = None,
) -> list[Memory]:
    return repository.get_memories(
        db,
        limit,
        owner_key,
        profile_id,
    )


def create_task(
    db: DBSession,
    title: str,
    description: str,
    priority: int = 3,
    agent: str = "general",
    session_id: str | None = None,
    parent_task_id: str | None = None,
    max_retries: int = 3,
) -> Task:
    return repository.create_task(
        db,
        title,
        description,
        priority,
        agent,
        session_id,
        parent_task_id,
        max_retries,
    )


def get_task(
    db: DBSession,
    task_id: str,
) -> Task | None:
    return repository.get_task(
        db,
        task_id,
    )


def get_tasks(
    db: DBSession,
    status: str | None = None,
    limit: int = 100,
) -> list[Task]:
    return repository.get_tasks(
        db,
        status,
        limit,
    )


def update_task(
    db: DBSession,
    task_id: str,
    **updates: Any,
) -> Task | None:
    return repository.update_task(
        db,
        task_id,
        **updates,
    )


def create_action(
    db: DBSession,
    tool: str,
    permission: str,
    risk: str,
    capability: str | None = None,
    session_id: str | None = None,
    task_id: str | None = None,
    arguments: dict | None = None,
    permission_allowed: bool = False,
    permission_reason: str | None = None,
) -> ActionLog:
    return repository.create_action(
        db,
        tool,
        permission,
        risk,
        capability,
        session_id,
        task_id,
        arguments,
        permission_allowed,
        permission_reason,
    )


def complete_action(
    db: DBSession,
    action_id: str,
    result: Any = None,
) -> ActionLog | None:
    return repository.complete_action(
        db,
        action_id,
        result,
    )


def fail_action(
    db: DBSession,
    action_id: str,
    error: str,
) -> ActionLog | None:
    return repository.fail_action(
        db,
        action_id,
        error,
    )


def get_actions(
    db: DBSession,
    session_id: str | None = None,
    task_id: str | None = None,
    tool: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[ActionLog]:
    return repository.get_actions(
        db,
        session_id,
        task_id,
        tool,
        status,
        limit,
    )