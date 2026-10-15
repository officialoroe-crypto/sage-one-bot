from datetime import datetime, timezone

from database.models import ActionEvidence
from evidence.service import EvidenceService


def test_evidence_retrieval_deserializes_content(monkeypatch):
    class Result:
        def all(self):
            return [
                ActionEvidence(
                    id="evidence-1",
                    action_id="action-1",
                    mission_id="mission-1",
                    task_id="task-1",
                    parent_action_id=None,
                    evidence_type="execution_verification",
                    content='{"passed": true}',
                    verified=1,
                    created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
                )
            ]

    class DB:
        def scalars(self, query):
            self.query = query
            return Result()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

        def close(self):
            self.closed = True

    db = DB()
    monkeypatch.setattr("evidence.service.SessionLocal", lambda: db)

    rows = EvidenceService().list(
        task_id="task-1",
        verified_only=True,
        limit=10,
    )

    assert rows[0]["id"] == "evidence-1"
    assert rows[0]["content"] == {"passed": True}
    assert rows[0]["verified"] is True
    assert db.closed is True


def test_evidence_limit_is_bounded(monkeypatch):
    class DB:
        def scalars(self, query):
            self.query = query
            return type("R", (), {"all": lambda self: []})()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.close()

        def close(self):
            pass

    db = DB()
    monkeypatch.setattr("evidence.service.SessionLocal", lambda: db)

    EvidenceService().list(limit=9999)
    assert db.query is not None
