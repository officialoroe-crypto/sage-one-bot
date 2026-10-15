from missions import api


class FakeMissionEngine:
    def get_mission(self, mission_id):
        if mission_id == "missing":
            return None
        return {
            "id": mission_id,
            "status": "executing",
            "current_task_id": "task-1",
        }

    def get_tasks(self, mission_id):
        return [
            {
                "id": "task-1",
                "status": "completed",
                "verification_status": "verified",
            },
            {
                "id": "task-2",
                "status": "running",
                "verification_status": "pending",
            },
            {
                "id": "task-3",
                "status": "pending",
                "verification_status": "pending",
            },
        ]


class FakeMissionIntelligence:
    def set_status(self, mission_id, status):
        return {
            "id": mission_id,
            "status": "executing" if status == "resumed" else status,
        }


def test_mission_router_exposes_control_and_history_routes():
    paths = {(route.path, tuple(sorted(route.methods or []))) for route in api.router.routes}

    assert ("/missions/{mission_id}/progress", ("GET",)) in paths
    assert ("/missions/{mission_id}/events", ("GET",)) in paths
    assert ("/missions/{mission_id}/pause", ("POST",)) in paths
    assert ("/missions/{mission_id}/resume", ("POST",)) in paths
    assert ("/missions/{mission_id}/cancel", ("POST",)) in paths


def test_mission_api_router_is_registered_in_fastapi_app():
    from app.main import app

    paths = app.openapi()["paths"]

    assert "/missions/{mission_id}/progress" in paths
    assert "/missions/{mission_id}/events" in paths
    assert "/missions/{mission_id}/pause" in paths
    assert "/missions/{mission_id}/resume" in paths
    assert "/missions/{mission_id}/cancel" in paths


def test_progress_summary_uses_verified_task_completion(monkeypatch):
    monkeypatch.setattr(api, "mission_engine", FakeMissionEngine())

    result = api._progress("mission-1")

    assert result["mission_id"] == "mission-1"
    assert result["total_tasks"] == 3
    assert result["completed_tasks"] == 1
    assert result["running_tasks"] == 1
    assert result["pending_tasks"] == 1
    assert result["failed_tasks"] == 0
    assert result["progress_percent"] == 33.33


def test_control_action_persists_history(monkeypatch):
    monkeypatch.setattr(api, "mission_engine", FakeMissionEngine())
    monkeypatch.setattr(api, "mission_intelligence", FakeMissionIntelligence())

    recorded = []

    def fake_append_event(*, mission_id, event):
        recorded.append((mission_id, event))
        return {"id": "event-1", "sequence": 1}

    monkeypatch.setattr(api, "append_event", fake_append_event)

    result = api.pause_mission("mission-1")

    assert result["success"] is True
    assert result["action"] == "pause"
    assert recorded[0][0] == "mission-1"
    assert recorded[0][1]["event_type"] == "mission_paused"
    assert recorded[0][1]["status"] == "paused"


def test_control_history_failure_does_not_break_success(monkeypatch):
    monkeypatch.setattr(api, "mission_engine", FakeMissionEngine())
    monkeypatch.setattr(api, "mission_intelligence", FakeMissionIntelligence())

    def failing_append_event(*, mission_id, event):
        raise RuntimeError("history unavailable")

    monkeypatch.setattr(api, "append_event", failing_append_event)

    result = api.resume_mission("mission-1")

    assert result["success"] is True
    assert result["action"] == "resume"
    assert result["mission"]["status"] == "executing"
