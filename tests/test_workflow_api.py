from fastapi.testclient import TestClient

from app.main import app
from identity.auth import authenticate_request


def test_workspace_and_project_roundtrip(monkeypatch):
    ident = {"auth_provider": "test", "auth_subject": "wf-owner-1", "name": "Wf", "email": None}
    app.dependency_overrides[authenticate_request] = lambda: dict(ident)
    try:
        c = TestClient(app)
        assert c.get("/workflow/workspaces").status_code == 200
        r = c.post("/workflow/workspaces", json={"name": "OROE", "slug": "oroe-wf1"})
        assert r.status_code == 200, r.text
        wid = r.json()["workspace"]["id"]
        assert any(w["id"] == wid for w in c.get("/workflow/workspaces").json()["workspaces"])
        p = c.post(f"/workflow/workspaces/{wid}/projects", json={"name": "Spring drop"})
        assert p.status_code == 200, p.text
        assert c.get(f"/workflow/workspaces/{wid}/projects").json()["projects"]
    finally:
        app.dependency_overrides.pop(authenticate_request, None)


def test_sessions_list_and_task_ownership():
    from app.main import _require_owner
    from database.connection import SessionLocal
    from database import repository

    def ident(sub):
        return {"auth_provider": "test", "auth_subject": sub, "name": sub, "email": None, "owner_mode": True}

    cur = {"v": ident("sess-owner-a")}
    app.dependency_overrides[authenticate_request] = lambda: dict(cur["v"])
    app.dependency_overrides[_require_owner] = lambda: dict(cur["v"])
    try:
        c = TestClient(app)
        r = c.post("/command", json={"message": "Plan my week please"})
        assert r.status_code == 200, r.text
        sid, tid = r.json()["session_id"], r.json()["task"]["id"]
        titles = [s["title"] for s in c.get("/sessions").json()["sessions"]]
        assert "Plan my week please" in titles
        assert c.get(f"/tasks/{tid}").status_code == 200
        # another owner must not see it
        cur["v"] = ident("sess-owner-b")
        assert c.get(f"/tasks/{tid}").status_code == 404
        assert all(t["id"] != tid for t in c.get("/tasks").json()["tasks"])
        assert "Plan my week please" not in [s["title"] for s in c.get("/sessions").json()["sessions"]]
    finally:
        app.dependency_overrides.pop(authenticate_request, None)
        app.dependency_overrides.pop(_require_owner, None)
