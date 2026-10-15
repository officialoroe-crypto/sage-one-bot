from sqlalchemy import create_engine

from database.connection import Base
from economy.service import get_evolution
from missions.engine import MissionEngine


def test_verified_mission_task_awards_evolution_once(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'verified-task.db'}")
    Base.metadata.create_all(engine)

    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr("missions.engine.SessionLocal", Session)

    mission_engine = MissionEngine()
    mission = mission_engine.create_mission("Complete a verified test mission")
    task = mission_engine.create_task(
        mission["id"],
        "Verified task",
        "Complete and verify this task",
    )

    first = mission_engine.verify_task(
        task["id"],
        passed=True,
        evidence="Test evidence proves the result.",
    )

    assert first["verification_status"] == "verified"
    assert first["achievement"]["created"] is True
    assert first["achievement"]["amount"] == 100

    with Session() as db:
        assert get_evolution(db, "developer:local-owner").lifetime_achievement == 100

    second = mission_engine.verify_task(
        task["id"],
        passed=True,
        evidence="The same verified result is replayed.",
    )

    assert second["achievement"]["created"] is False

    with Session() as db:
        assert get_evolution(db, "developer:local-owner").lifetime_achievement == 100
