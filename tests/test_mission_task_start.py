from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from database.models import ExecutionAttempt
from missions.engine import MissionEngine


def test_start_task_creates_attempt_atomically(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'mission-start.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr("missions.engine.SessionLocal", Session)

    mission_engine = MissionEngine()
    mission = mission_engine.create_mission("Atomic start")
    task = mission_engine.create_task(
        mission["id"],
        "Atomic task",
        "Start this task",
    )

    started = mission_engine.start_task(task["id"])

    assert started["task"]["status"] == "running"

    with Session() as db:
        attempt = db.query(ExecutionAttempt).filter(
            ExecutionAttempt.id == started["attempt_id"]
        ).one()
        assert attempt.task_id == task["id"]
        assert attempt.status == "running"
