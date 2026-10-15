from database.connection import SessionLocal
from database.repository import repository
from events.service import event_store


def serialize(notification):
    return {
        "id": notification.id,
        "task_id": notification.task_id,
        "session_id": notification.session_id,
        "type": notification.notification_type,
        "title": notification.title,
        "body": notification.body,
        "read": notification.read_at is not None,
        "read_at": notification.read_at.isoformat() if notification.read_at else None,
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
    }


def create_task_notification(
    task: dict,
    *,
    success: bool,
    body: str | None = None,
    owner_key: str | None = None,
):
    status = "completed" if success else "failed"
    title = "SAGE task completed" if success else "SAGE task failed"
    default_body = (
        f"{task.get('title', 'Background task')} finished successfully."
        if success
        else f"{task.get('title', 'Background task')} needs attention."
    )
    db = SessionLocal()
    try:
        notification = repository.create_notification(
            db,
            title=title,
            body=body or default_body,
            notification_type=f"task.{status}",
            task_id=task.get("id"),
            session_id=task.get("session_id"),
            owner_key=owner_key or task.get("owner_key"),
        )
        event_store.emit(
            event_type="NotificationCreated",
            task_id=notification.task_id,
            session_id=notification.session_id,
            status="created",
            payload={
                "notification_id": notification.id,
                "type": notification.notification_type,
                "title": notification.title,
            },
        )
        return serialize(notification)
    finally:
        db.close()


def list_notifications(
    session_id: str | None = None,
    unread_only: bool = False,
    limit: int = 50,
    owner_key: str | None = None,
):
    db = SessionLocal()
    try:
        return [
            serialize(item)
            for item in repository.get_notifications(
                db,
                session_id=session_id,
                unread_only=unread_only,
                limit=limit,
                owner_key=owner_key,
            )
        ]
    finally:
        db.close()


def mark_read(notification_id: str, owner_key: str | None = None):
    db = SessionLocal()
    try:
        item = repository.mark_notification_read(db, notification_id, owner_key=owner_key)
        return serialize(item) if item else None
    finally:
        db.close()


def mark_all_read(session_id: str | None = None, owner_key: str | None = None):
    db = SessionLocal()
    try:
        return repository.mark_all_notifications_read(db, session_id=session_id, **({"owner_key": owner_key} if owner_key is not None else {}))
    finally:
        db.close()
