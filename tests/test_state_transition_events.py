from events.service import SQLAlchemyEventStore


def test_event_store_serializes_structured_payload(monkeypatch):
    class FakeDB:
        def __init__(self):
            self.row = None

        def add(self, row):
            self.row = row

        def commit(self):
            return None

        def rollback(self):
            return None

        def close(self):
            return None

    db = FakeDB()
    monkeypatch.setattr(
        "events.service.SessionLocal",
        lambda: db,
    )

    event_id = SQLAlchemyEventStore().emit(
        event_type="TaskCompleted",
        task_id="task-1",
        mission_id="mission-1",
        session_id="session-1",
        status="completed",
        payload={"result": {"ok": True}},
    )

    assert event_id
    assert db.row.event_type == "TaskCompleted"
    assert db.row.task_id == "task-1"
    assert db.row.mission_id == "mission-1"
    assert '"ok": true' in db.row.payload


def test_event_store_rolls_back_failed_persistence(monkeypatch):
    class FakeDB:
        def add(self, row):
            raise RuntimeError("database unavailable")

        def commit(self):
            raise AssertionError("commit should not run")

        def rollback(self):
            self.rolled_back = True

        def close(self):
            self.closed = True

    db = FakeDB()
    monkeypatch.setattr(
        "events.service.SessionLocal",
        lambda: db,
    )

    try:
        SQLAlchemyEventStore().emit(
            event_type="TaskFailed",
            task_id="task-1",
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected persistence error")

    assert db.rolled_back is True
    assert db.closed is True
