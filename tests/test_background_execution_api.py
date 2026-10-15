from fastapi.testclient import TestClient

from app.main import _require_owner, app


client = TestClient(app)


def test_background_execution_queues_durable_task(monkeypatch):
    monkeypatch.setitem(
        app.dependency_overrides,
        _require_owner,
        lambda: {
            "auth_provider": "developer",
            "auth_subject": "local-owner",
            "owner_mode": True,
        },
    )
    captured = {}
    created = {
        "id": "task-bg-1",
        "title": "Research the market",
        "description": "Research the market",
        "status": "pending",
        "agent": "research",
    }

    monkeypatch.setattr("app.main.agents.choose", lambda goal: "research")
    monkeypatch.setattr("app.main.agents.exists", lambda name: name == "research")

    def create(**kwargs):
        captured.update(kwargs)
        return created

    monkeypatch.setattr("app.main.tasks.create", create)

    response = client.post(
        "/execute/background",
        json={
            "goal": "Research the market",
            "session_id": "session-1",
            "max_steps": 20,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["status"] == "queued"
    assert body["task"]["id"] == "task-bg-1"
    assert captured == {
        "title": "Research the market",
        "description": "Research the market",
        "priority": 3,
        "agent": "research",
        "session_id": "session-1",
        "owner_key": "developer:local-owner",
        "profile_id": captured["profile_id"],
        "project_id": None,
    }


def test_background_execution_does_not_run_in_request(monkeypatch):
    app.dependency_overrides[_require_owner] = lambda: {
        "auth_provider": "developer",
        "auth_subject": "local-owner",
        "owner_mode": True,
    }
    created = {
        "id": "task-bg-2",
        "title": "Do work later",
        "description": "Do work later",
        "status": "pending",
    }

    monkeypatch.setattr("app.main.agents.choose", lambda goal: "general")
    monkeypatch.setattr("app.main.agents.exists", lambda name: True)
    monkeypatch.setattr("app.main.tasks.create", lambda **kwargs: created)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("background execution must not run inference in the HTTP request")

    monkeypatch.setattr("app.main.execution_engine.execute_mission", fail_if_called)
    monkeypatch.setattr("app.main.planner.plan", fail_if_called)

    response = client.post(
        "/execute/background",
        json={"goal": "Do work later"},
    )

    assert response.status_code == 200
    assert response.json()["task"]["id"] == "task-bg-2"
