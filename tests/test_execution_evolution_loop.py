from fastapi.testclient import TestClient

from app.main import app
from economy.service import evolution_progress


def test_worker_lifecycle_endpoint_exists(monkeypatch):
    monkeypatch.setattr("app.main.worker_service.health", lambda: {
        "enabled": True,
        "running": True,
        "worker_id": "test-worker",
        "last_result": {"task": "private-output"},
        "last_error": "private-error",
    })
    with TestClient(app) as client:
        response = client.get("/worker/health")
    assert response.status_code == 200
    assert response.json()["worker"] == {
        "enabled": True,
        "running": True,
    }

    details = client.get("/worker/health/details")
    assert details.status_code == 200
    assert details.json()["worker"]["last_result"] == {"task": "private-output"}


def test_evolution_simulation_is_non_mutating(monkeypatch):
    from database.connection import Base, SessionLocal, engine
    from economy.service import get_evolution, evolution_simulation

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        profile = get_evolution(db, "developer:test-owner")
        assert profile.lifetime_achievement == 0
        simulation = evolution_simulation(db, "developer:test-owner", 6000, 2000)
        assert simulation["simulation"] is True
        assert simulation["mutated"] is False
        assert simulation["from"]["lifetime_achievement"] == 0
        assert simulation["to"]["lifetime_achievement"] == 6000
        assert simulation["to"]["tier"] == "Gold"
        assert simulation["duration_ms"] == 2000

        persisted = get_evolution(db, "developer:test-owner")
        assert persisted.lifetime_achievement == 0
        assert evolution_progress(6000)["next_tier"] == "Platinum"
