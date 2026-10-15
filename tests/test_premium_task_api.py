from fastapi.testclient import TestClient

from app import main as main_module
from app.main import _require_owner, app
from identity.auth import authenticate_request


client = TestClient(app)


def test_premium_task_creation_uses_trusted_owner_and_catalog_key(monkeypatch):
    claims = {
        "auth_provider": "developer",
        "auth_subject": "dev:owner-subject",
        "owner_mode": True,
    }
    monkeypatch.setitem(app.dependency_overrides, _require_owner, lambda: claims)
    captured = {}
    created = {
        "id": "premium-api-task",
        "status": "pending",
        "premium_work_key": "research_deep",
    }

    def create_task(**kwargs):
        captured.update(kwargs)
        return created

    monkeypatch.setattr(main_module.tasks, "create", create_task)

    response = client.post(
        "/tasks/premium",
        json={
            "title": "Deep research",
            "description": "Research a topic",
            "work_key": "research_deep",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    assert captured["owner_key"] == "developer:dev:owner-subject"
    assert captured["premium_work_key"] == "research_deep"
    assert "amount" not in captured
    assert "owner_key" not in response.json()["task"]


def test_premium_task_creation_rejects_unknown_catalog_key(monkeypatch):
    claims = {
        "auth_provider": "developer",
        "auth_subject": "dev:owner-subject",
        "owner_mode": True,
    }
    monkeypatch.setitem(app.dependency_overrides, _require_owner, lambda: claims)
    called = {"value": False}

    def create_task(**_kwargs):
        called["value"] = True
        return {"id": "should-not-exist"}

    monkeypatch.setattr(main_module.tasks, "create", create_task)

    response = client.post(
        "/tasks/premium",
        json={
            "title": "Unknown premium work",
            "description": "Should not be queued",
            "work_key": "custom_price_1",
        },
    )

    assert response.status_code == 422
    assert called["value"] is False


def test_premium_task_creation_rejects_non_owner(monkeypatch):
    claims = {
        "auth_provider": "google",
        "auth_subject": "regular-user",
        "owner_mode": False,
    }
    monkeypatch.setitem(app.dependency_overrides, authenticate_request, lambda: claims)
    called = {"value": False}

    def create_task(**_kwargs):
        called["value"] = True
        return {"id": "should-not-exist"}

    monkeypatch.setattr(main_module.tasks, "create", create_task)

    response = client.post(
        "/tasks/premium",
        json={
            "title": "Premium work",
            "description": "Should be forbidden",
            "work_key": "research_deep",
        },
    )

    assert response.status_code == 403
    assert called["value"] is False
