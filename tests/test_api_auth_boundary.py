from fastapi.testclient import TestClient
from starlette.requests import Request

from app.main import _require_api_access, app
from config.settings import settings


def _request(path: str, host: str = "127.0.0.1") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [],
            "client": (host, 12345),
            "server": ("localhost", 8010),
            "scheme": "http",
        }
    )


def test_main_api_requires_identity_when_developer_mode_is_disabled(monkeypatch):
    monkeypatch.setattr(settings, "DEVELOPER_MODE", False)
    client = TestClient(app)
    override = app.dependency_overrides.pop(_require_api_access, None)
    try:
        response = client.get("/orchestrator")
    finally:
        if override is not None:
            app.dependency_overrides[_require_api_access] = override

    assert response.status_code == 401


def test_main_api_allows_local_developer_mode(monkeypatch):
    monkeypatch.setattr(settings, "DEVELOPER_MODE", True)

    _require_api_access(_request("/orchestrator", "127.0.0.1"))


def test_public_health_remains_available_without_identity(monkeypatch):
    monkeypatch.setattr(settings, "DEVELOPER_MODE", False)
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
