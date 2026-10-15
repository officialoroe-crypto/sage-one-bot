from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_notifications_api_lists_unread(monkeypatch):
    expected = [
        {
            "id": "n-1",
            "task_id": "task-1",
            "title": "SAGE task completed",
            "body": "Done",
            "read": False,
        }
    ]
    monkeypatch.setattr("app.main.list_notifications", lambda **kwargs: expected)

    response = client.get("/notifications?unread_only=true&limit=10")

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["notifications"] == expected


def test_notification_can_be_marked_read(monkeypatch):
    expected = {
        "id": "n-1",
        "task_id": "task-1",
        "read": True,
    }
    monkeypatch.setattr("app.main.mark_read", lambda notification_id, owner_key=None: expected)

    response = client.post("/notifications/n-1/read")

    assert response.status_code == 200
    assert response.json()["notification"] == expected


def test_missing_notification_returns_404(monkeypatch):
    monkeypatch.setattr("app.main.mark_read", lambda notification_id, owner_key=None: None)

    response = client.post("/notifications/missing/read")

    assert response.status_code == 404


def test_mark_all_notifications_read(monkeypatch):
    monkeypatch.setattr("app.main.mark_all_read", lambda session_id=None, owner_key=None: 3)

    response = client.post("/notifications/read-all")

    assert response.status_code == 200
    assert response.json()["marked_read"] == 3
