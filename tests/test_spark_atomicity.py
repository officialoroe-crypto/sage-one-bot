import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from economy.models import EvolutionProfile, SparkLedgerEntry, SparkWallet
from economy.service import grant_sparks, spend_sparks, snapshot


@pytest.fixture
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'economy.db'}")
    Base.metadata.create_all(
        engine,
        tables=[SparkWallet.__table__, SparkLedgerEntry.__table__, EvolutionProfile.__table__],
    )
    Session = sessionmaker(bind=engine)
    with Session() as session:
        yield session
    engine.dispose()


def test_spend_reference_is_idempotent(db_session):
    grant_sparks(db_session, "owner", 100, "welcome", reference="grant-1")
    first = spend_sparks(db_session, "owner", 40, "premium", reference="job-1")
    second = spend_sparks(db_session, "owner", 40, "premium-retried", reference="job-1")

    assert second.id == first.id
    assert snapshot(db_session, "owner")["spark"]["balance"] == 60
    assert snapshot(db_session, "owner")["spark"]["lifetime_spent"] == 40


def test_reusing_spend_reference_with_different_amount_is_rejected(db_session):
    grant_sparks(db_session, "owner", 100, "welcome")
    spend_sparks(db_session, "owner", 40, "premium", reference="job-1")

    with pytest.raises(ValueError, match="different amount"):
        spend_sparks(db_session, "owner", 30, "premium", reference="job-1")


def test_atomic_spend_never_overdraws(db_session):
    grant_sparks(db_session, "owner", 100, "welcome")
    spend_sparks(db_session, "owner", 70, "job-a", reference="a")

    with pytest.raises(ValueError, match="Insufficient"):
        spend_sparks(db_session, "owner", 40, "job-b", reference="b")

    data = snapshot(db_session, "owner")
    assert data["spark"]["balance"] == 30
    assert data["spark"]["lifetime_spent"] == 70


def test_grant_reference_is_idempotent(db_session):
    first = grant_sparks(db_session, "owner", 25, "reward", reference="reward-1")
    second = grant_sparks(db_session, "owner", 25, "reward-retry", reference="reward-1")

    assert second.id == first.id
    data = snapshot(db_session, "owner")
    assert data["spark"]["balance"] == 25
    assert data["spark"]["lifetime_earned"] == 25
