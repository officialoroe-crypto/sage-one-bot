import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from economy.achievements import VerifiedAchievementEvent, record_verified_achievement
from economy.models import EvolutionProfile


@pytest.fixture
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'verified-achievements.db'}")
    Base.metadata.create_all(
        engine,
        tables=[EvolutionProfile.__table__, VerifiedAchievementEvent.__table__],
    )
    Session = sessionmaker(bind=engine)
    with Session() as session:
        yield session
    engine.dispose()


def test_verified_achievement_creates_event_and_evolution(db_session):
    event, created = record_verified_achievement(
        db_session,
        "google:verified-user",
        1_000,
        "completed verified mission",
        "mission",
        "mission-123",
        {"verification": "all required criteria passed"},
    )

    assert created is True
    assert event.verification_status == "verified"
    assert event.source_type == "mission"
    assert event.source_id == "mission-123"

    profile = db_session.get(EvolutionProfile, "google:verified-user")
    assert profile is not None
    assert profile.lifetime_achievement == 1_000
    assert profile.tier == "Silver"


def test_verified_achievement_is_idempotent_for_same_source(db_session):
    owner = "google:idempotent-user"
    evidence = {"verification": "mission result and artifact verified"}

    first, created_first = record_verified_achievement(
        db_session, owner, 500, "verified result", "mission", "mission-456", evidence
    )
    second, created_second = record_verified_achievement(
        db_session, owner, 500, "verified result", "mission", "mission-456", evidence
    )

    assert created_first is True
    assert created_second is False
    assert first.id == second.id

    profile = db_session.get(EvolutionProfile, owner)
    assert profile.lifetime_achievement == 500
    events = db_session.scalars(
        select(VerifiedAchievementEvent).where(VerifiedAchievementEvent.owner_key == owner)
    ).all()
    assert len(events) == 1


def test_verified_achievement_requires_evidence(db_session):
    with pytest.raises(ValueError, match="evidence"):
        record_verified_achievement(
            db_session,
            "google:evidence-user",
            100,
            "missing evidence",
            "mission",
            "mission-789",
            {},
        )
