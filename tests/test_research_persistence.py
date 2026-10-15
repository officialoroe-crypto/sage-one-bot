from app.worker import SageWorker


def test_research_worker_persists_successful_report(monkeypatch):
    captured = {}

    def synthesize(**kwargs):
        return {
            "success": True,
            "question": kwargs["question"],
            "summary": "A durable report.",
            "source_count": 2,
            "evidence_count": 3,
            "claim_count": 1,
            "claims": [
                {
                    "claim_id": "c1",
                    "claim": "Supported finding",
                    "source_ids": ["s1"],
                    "supporting_evidence": ["e1"],
                }
            ],
        }

    def save(report, **kwargs):
        captured["report"] = report
        captured["kwargs"] = kwargs
        return {"research_id": "research-123"}

    monkeypatch.setattr(
        "app.worker.research_synthesis_engine.synthesize",
        synthesize,
    )
    monkeypatch.setattr(
        "app.worker.research_persistence.save",
        save,
    )

    worker = SageWorker(worker_id="test-worker")
    result = worker._execute_task_payload(
        {
            "id": "task-123",
            "description": "Research: durable research storage",
            "agent": "research",
            "session_id": "session-123",
        }
    )

    assert result["success"] is True
    assert result["research_id"] == "research-123"
    assert captured["kwargs"] == {
        "task_id": "task-123",
        "session_id": "session-123",
    }
    assert captured["report"]["claim_count"] == 1


def test_failed_research_report_is_not_persisted(monkeypatch):
    called = False

    def synthesize(**kwargs):
        return {
            "success": False,
            "question": kwargs["question"],
            "error": "No usable evidence.",
        }

    def save(*args, **kwargs):
        nonlocal called
        called = True
        return {"research_id": "unexpected"}

    monkeypatch.setattr(
        "app.worker.research_synthesis_engine.synthesize",
        synthesize,
    )
    monkeypatch.setattr(
        "app.worker.research_persistence.save",
        save,
    )

    worker = SageWorker(worker_id="test-worker")
    result = worker._execute_task_payload(
        {
            "id": "task-456",
            "description": "Research: unavailable topic",
            "agent": "research",
            "session_id": "session-456",
        }
    )

    assert result["success"] is False
    assert called is False
