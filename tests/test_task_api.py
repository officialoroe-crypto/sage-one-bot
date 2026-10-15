from fastapi.testclient import TestClient

import pytest

from app.main import _require_owner, app
from identity.auth import authenticate_request

client = TestClient(app)
_OWNER = {"auth_provider": "test", "auth_subject": "task-api-owner", "name": "Owner", "email": None, "owner_mode": True}


@pytest.fixture(autouse=True)
def owner_identity():
    app.dependency_overrides[authenticate_request] = lambda: dict(_OWNER)
    app.dependency_overrides[_require_owner] = lambda: dict(_OWNER)
    yield
    app.dependency_overrides.pop(authenticate_request, None)
    app.dependency_overrides.pop(_require_owner, None)


def test_task_api_creates_and_reads_durable_task(monkeypatch):
    created = {
        "id": "task-1",
        "title": "Background test",
        "description": "do a light task",
        "status": "pending",
    }

    monkeypatch.setattr("app.main.tasks.create", lambda **kwargs: created)
    monkeypatch.setattr("app.main.tasks.get", lambda task_id, owner_key=None: created if task_id == "task-1" else None)

    response = client.post(
        "/tasks",
        json={
            "title": "Background test",
            "description": "do a light task",
            "priority": 3,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert response.json()["task"]["id"] == "task-1"

    response = client.get("/tasks/task-1")
    assert response.status_code == 200
    assert response.json()["task"]["status"] == "pending"


def test_task_api_rejects_invalid_status(monkeypatch):
    response = client.get("/tasks?status=not-a-real-status")
    assert response.status_code == 400
