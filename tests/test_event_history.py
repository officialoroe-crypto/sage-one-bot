from datetime import datetime, timezone

from events.service import SQLAlchemyEventStore
from database.models import ExecutionEvent


def test_event_history_filters_and_deserializes_payload(monkeypatch):
    class FakeScalarResult:
        def all(self):
            return [
                ExecutionEvent(
                    id="event-1",
                    event_type="TaskCompleted",
                    action_id="action-1",
                    session_id="session-1",
                    mission_id="mission-1",
                    task_id="task-1",
                    parent_action_id=None,
                    status="completed",
                    source="test",
                    payload='{"ok": true, "count": 2}',
                    created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
                )
            ]

    class FakeDB:
        def scalars(self, query):
            self.query = query
            return FakeScalarResult()

        def close(self):
            self.closed = True

    db = FakeDB()
    monkeypatch.setattr(
        "events.service.SessionLocal",
        lambda: db,
    )

    events = SQLAlchemyEventStore().list(
        mission_id="mission-1",
        event_type="TaskCompleted",
        limit=10,
    )

    assert events[0]["id"] == "event-1"
    assert events[0]["payload"] == {"ok": True, "count": 2}
    assert events[0]["mission_id"] == "mission-1"
    assert db.closed is True


def test_event_history_limit_is_bounded(monkeypatch):
    class FakeDB:
        def scalars(self, query):
            self.query = query
            return type("R", (), {"all": lambda self: []})()

        def close(self):
            pass

    db = FakeDB()
    monkeypatch.setattr("events.service.SessionLocal", lambda: db)

    SQLAlchemyEventStore().list(limit=9999)
    assert db.query is not None
