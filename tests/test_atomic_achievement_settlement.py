from sqlalchemy import select

from database.connection import Base, SessionLocal, engine
from economy import achievements
from economy.achievements import VerifiedAchievementEvent, record_verified_achievement
from economy.service import get_evolution


def _reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_verified_achievement_updates_evolution_atomically():
    _reset_database()

    with SessionLocal() as db:
        event, created = record_verified_achievement(
            db,
            "test-owner",
            250,
            "Verified mission result",
            "mission",
            "mission-1",
            {"status": "verified", "result": "done"},
        )
        assert created is True
        assert event.amount == 250
        assert get_evolution(db, "test-owner").lifetime_achievement == 250

        duplicate, created_again = record_verified_achievement(
            db,
            "test-owner",
            250,
            "Verified mission result",
            "mission",
            "mission-1",
            {"status": "verified", "result": "done"},
        )
        assert created_again is False
        assert duplicate.id == event.id
        assert get_evolution(db, "test-owner").lifetime_achievement == 250


def test_verified_achievement_rolls_back_event_and_evolution_on_failure(monkeypatch):
    _reset_database()

    def fail_settlement(*args, **kwargs):
        raise RuntimeError("simulated settlement failure")

    monkeypatch.setattr(achievements, "record_achievement", fail_settlement)

    with SessionLocal() as db:
        try:
            record_verified_achievement(
                db,
                "test-owner",
                250,
                "Verified mission result",
                "mission",
                "mission-rollback",
                {"status": "verified"},
            )
        except RuntimeError as exc:
            assert str(exc) == "simulated settlement failure"
        else:
            raise AssertionError("Expected simulated settlement failure")

    with SessionLocal() as db:
        assert db.scalar(
            select(VerifiedAchievementEvent).where(
                VerifiedAchievementEvent.owner_key == "test-owner",
                VerifiedAchievementEvent.source_id == "mission-rollback",
            )
        ) is None
        assert get_evolution(db, "test-owner").lifetime_achievement == 0
