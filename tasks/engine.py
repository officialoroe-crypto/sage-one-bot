from datetime import datetime, timezone

from database.connection import SessionLocal
from events.service import event_store
from database.repository import repository


class TaskEngine:

    VALID_STATUSES = {
        "pending",
        "running",
        "paused",
        "completed",
        "failed",
        "cancelled",
    }

    def create(
        self,
        title: str,
        description: str,
        priority: int = 3,
        agent: str = "general",
        session_id: str | None = None,
        parent_task_id: str | None = None,
        owner_key: str | None = None,
        premium_work_key: str | None = None,
        profile_id: str | None = None,
        project_id: str | None = None,
    ):
        priority = max(1, min(priority, 5))
        db = SessionLocal()

        try:
            task = repository.create_task(
                db=db,
                title=title,
                description=description,
                priority=priority,
                agent=agent,
                session_id=session_id,
                parent_task_id=parent_task_id,
                owner_key=owner_key,
                premium_work_key=premium_work_key,
                profile_id=profile_id,
                project_id=project_id,
            )
            return self.serialize(task)
        finally:
            db.close()

    def get(self, task_id: str, owner_key: str | None = None):
        db = SessionLocal()
        try:
            task = repository.get_task(db, task_id, owner_key=owner_key)
            return self.serialize(task) if task else None
        finally:
            db.close()

    def list(self, status: str | None = None, owner_key: str | None = None):
        db = SessionLocal()
        try:
            tasks = repository.get_tasks(db, status=status, owner_key=owner_key)
            return [self.serialize(task) for task in tasks]
        finally:
            db.close()

    def claim_next(
        self,
        worker_id: str,
        lease_seconds: int = 120,
    ):
        db = SessionLocal()
        try:
            task = repository.claim_next_task(
                db,
                worker_id,
                lease_seconds,
            )
            return self.serialize(task) if task else None
        finally:
            db.close()

    def claim_next_root(
        self,
        worker_id: str,
        lease_seconds: int = 120,
    ):
        """Atomically claim only top-level durable tasks.

        Mission child tasks are executed by their owning mission execution
        loop. They must not enter the global worker queue and race another
        worker against the mission that owns them.
        """
        from database.models import Task

        now = datetime.now(timezone.utc)
        lease_seconds = max(30, int(lease_seconds))
        lease_time = datetime.fromtimestamp(
            now.timestamp() + lease_seconds,
            tz=timezone.utc,
        )

        db = SessionLocal()
        try:
            candidate = (
                db.query(Task.id)
                .filter(Task.status == "pending")
                .filter(Task.mission_id.is_(None))
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
                .filter(Task.status == "pending")
                .filter(Task.mission_id.is_(None))
                .filter(
                    (Task.next_retry_at.is_(None))
                    | (Task.next_retry_at <= now)
                )
                .update(
                    {
                        Task.status: "running",
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
            task = repository.get_task(db, task_id)
            if task:
                event_store.emit(
                    event_type="TaskClaimed",
                    task_id=task.id,
                    session_id=task.session_id,
                    status=task.status,
                    payload={"worker_id": worker_id, "lease_seconds": lease_seconds},
                )
            return self.serialize(task, include_owner=True) if task else None
        finally:
            db.close()

    def heartbeat(
        self,
        task_id: str,
        worker_id: str,
        lease_seconds: int = 120,
    ):
        db = SessionLocal()
        try:
            task = repository.heartbeat_task(
                db,
                task_id,
                worker_id,
                lease_seconds,
            )
            return self.serialize(task) if task else None
        finally:
            db.close()

    def start(self, task_id: str):
        db = SessionLocal()
        try:
            task = repository.update_task(
                db,
                task_id,
                status="running",
                progress=0,
                started_at=datetime.now(timezone.utc),
            )
            return self.serialize(task) if task else None
        finally:
            db.close()

    def progress(self, task_id: str, progress: int):
        progress = max(0, min(progress, 100))
        db = SessionLocal()
        try:
            task = repository.update_task(
                db,
                task_id,
                progress=progress,
            )
            return self.serialize(task) if task else None
        finally:
            db.close()

    def complete(self, task_id: str, result: str):
        db = SessionLocal()
        try:
            task = repository.update_task(
                db,
                task_id,
                status="completed",
                progress=100,
                result=result,
                error=None,
                completed_at=datetime.now(timezone.utc),
                worker_id=None,
                lease_expires_at=None,
                heartbeat_at=datetime.now(timezone.utc),
                next_retry_at=None,
            )
            if task:
                event_store.emit(
                    event_type="TaskCompleted",
                    task_id=task.id,
                    session_id=task.session_id,
                    mission_id=task.mission_id,
                    status=task.status,
                    payload={"result": result},
                )
            return self.serialize(task) if task else None
        finally:
            db.close()

    def complete_claim(
        self,
        task_id: str,
        worker_id: str,
        result: str,
    ):
        db = SessionLocal()
        try:
            task = repository.complete_task_claim(
                db,
                task_id,
                worker_id,
                result,
            )
            if task:
                event_store.emit(
                    event_type="TaskCompleted",
                    task_id=task.id,
                    session_id=task.session_id,
                    mission_id=task.mission_id,
                    status=task.status,
                    payload={"result": result},
                )
            return self.serialize(task) if task else None
        finally:
            db.close()

    def fail(self, task_id: str, error: str):
        db = SessionLocal()
        try:
            task = repository.get_task(db, task_id)
            if not task:
                return None

            new_retries = task.retries + 1
            status = (
                "pending"
                if new_retries < task.max_retries
                else "failed"
            )

            task = repository.update_task(
                db,
                task_id,
                status=status,
                retries=new_retries,
                error=error,
            )
            return self.serialize(task)
        finally:
            db.close()

    def fail_claim(
        self,
        task_id: str,
        worker_id: str,
        error: str,
        retry_delay_seconds: int,
    ):
        db = SessionLocal()
        try:
            task = repository.fail_task_claim(
                db,
                task_id,
                worker_id,
                error,
                retry_delay_seconds,
            )
            return self.serialize(task) if task else None
        finally:
            db.close()

    def recover_expired(self):
        db = SessionLocal()
        try:
            return repository.recover_expired_tasks(db)
        finally:
            db.close()

    def cancel(self, task_id: str, owner_key: str | None = None):
        db = SessionLocal()
        try:
            task = repository.update_task(
                db,
                task_id,
                owner_key=owner_key,
                status="cancelled",
                worker_id=None,
                lease_expires_at=None,
            )
            return self.serialize(task) if task else None
        finally:
            db.close()

    def serialize(self, task, *, include_owner: bool = False):
        payload = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "agent": task.agent,
            "session_id": task.session_id,
            "parent_task_id": task.parent_task_id,
            **({"project_id": task.project_id} if task.project_id else {}),
            "premium_work_key": task.premium_work_key,
            "mission_id": task.mission_id,
            "depends_on": task.depends_on,
            "progress": task.progress,
            "result": task.result,
            "error": task.error,
            "retries": task.retries,
            "max_retries": task.max_retries,
            "verification_status": task.verification_status,
            "worker_id": task.worker_id,
            "lease_expires_at": task.lease_expires_at.isoformat() if task.lease_expires_at else None,
            "heartbeat_at": task.heartbeat_at.isoformat() if task.heartbeat_at else None,
            "next_retry_at": task.next_retry_at.isoformat() if task.next_retry_at else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }
        if include_owner:
            payload["owner_key"] = task.owner_key
        return payload


tasks = TaskEngine()
