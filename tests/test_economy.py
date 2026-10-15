import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from economy.costs import cost_catalog, cost_for
from economy.models import EvolutionProfile, PremiumSparkTransaction, SparkLedgerEntry, SparkWallet
from economy.service import (
    EVOLUTION_TIERS, _tier_for, grant_sparks, record_achievement, refund_premium_sparks,
    reserve_premium_sparks, reserve_premium_work, settle_premium_sparks, spend_sparks, snapshot,
)


@pytest.fixture
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'economy.db'}")
    Base.metadata.create_all(
        engine,
        tables=[SparkWallet.__table__, SparkLedgerEntry.__table__, EvolutionProfile.__table__, PremiumSparkTransaction.__table__],
    )
    Session = sessionmaker(bind=engine)
    with Session() as session:
        yield session
    engine.dispose()


def test_evolution_thresholds_are_deterministic():
    assert _tier_for(0) == ("Bronze", "LOW")
    assert _tier_for(1_000) == ("Silver", "LOW")
    assert _tier_for(100_000_000) == ("Californium Overlord", "HIGH")


def test_evolution_snapshot_exposes_next_tier_progress(db_session):
    owner = "google:progress-user"
    record_achievement(db_session, owner, 2_000, "verified milestone")
    data = snapshot(db_session, owner)
    progress = data["evolution"]["progress"]
    assert data["evolution"]["tier"] == "Silver"
    assert progress["next_tier"] == "Gold"
    assert progress["current_threshold"] == 1_000
    assert progress["next_threshold"] == 5_000
    assert progress["ratio"] == pytest.approx(0.25)


def test_spark_ledger_preserves_balance_and_lifetime(db_session):
    owner = "google:test-user"
    grant_sparks(db_session, owner, 100, "welcome")
    spend_sparks(db_session, owner, 30, "premium task")
    data = snapshot(db_session, owner)
    assert data["spark"]["balance"] == 70
    assert data["spark"]["lifetime_earned"] == 100
    assert data["spark"]["lifetime_spent"] == 30
    assert [entry["delta"] for entry in data["ledger"]] == [-30, 100]


def test_spark_spend_cannot_overdraw(db_session):
    owner = "google:test-user"
    grant_sparks(db_session, owner, 10, "welcome")
    with pytest.raises(ValueError, match="Insufficient"):
        spend_sparks(db_session, owner, 11, "premium task")


def test_evolution_is_independent_of_spark_balance(db_session):
    owner = "google:evolution-user"
    grant_sparks(db_session, owner, 100, "welcome")
    spend_sparks(db_session, owner, 100, "premium task")
    profile = record_achievement(db_session, owner, 1_000, "verified milestone")
    assert profile.lifetime_achievement == 1_000
    assert profile.tier == "Silver"


def test_premium_work_cost_catalog_is_stable():
    keys = [item["key"] for item in cost_catalog()]
    assert keys == ["research_deep", "mission_heavy", "verification", "content_generation"]
    assert cost_for("research_deep") == 25


def test_evolution_tier_catalog_is_ordered_and_complete():
    assert len(EVOLUTION_TIERS) == 13
    thresholds = [threshold for threshold, _ in EVOLUTION_TIERS]
    assert thresholds == sorted(set(thresholds))
    assert EVOLUTION_TIERS[0] == (0, "Bronze")
    assert EVOLUTION_TIERS[-1] == (100_000_000, "Californium Overlord")


def test_premium_reservation_is_idempotent_and_debits_once(db_session):
    owner = "google:premium-user"
    grant_sparks(db_session, owner, 100, "welcome")

    first = reserve_premium_sparks(
        db_session, owner, "op-1", "research_deep", 25,
    )
    replay = reserve_premium_sparks(
        db_session, owner, "op-1", "research_deep", 25,
    )

    assert replay.id == first.id
    data = snapshot(db_session, owner)
    assert data["spark"]["balance"] == 75
    assert data["spark"]["lifetime_spent"] == 25
    assert [entry["delta"] for entry in data["ledger"]].count(-25) == 1


def test_premium_settlement_is_idempotent_without_second_charge(db_session):
    owner = "google:premium-settle"
    grant_sparks(db_session, owner, 100, "welcome")
    reserve_premium_sparks(db_session, owner, "op-2", "verification", 15)

    settled = settle_premium_sparks(db_session, owner, "op-2")
    replay = settle_premium_sparks(db_session, owner, "op-2")

    assert settled.status == "settled"
    assert replay.id == settled.id
    assert snapshot(db_session, owner)["spark"]["balance"] == 85


def test_premium_refund_is_idempotent_and_restores_balance_once(db_session):
    owner = "google:premium-refund"
    grant_sparks(db_session, owner, 100, "welcome")
    reserve_premium_sparks(db_session, owner, "op-3", "mission_heavy", 50)

    refunded = refund_premium_sparks(db_session, owner, "op-3", "execution failed")
    replay = refund_premium_sparks(db_session, owner, "op-3", "execution failed again")

    data = snapshot(db_session, owner)
    assert refunded.status == "refunded"
    assert replay.id == refunded.id
    assert data["spark"]["balance"] == 100
    assert data["spark"]["lifetime_spent"] == 50
    assert data["spark"]["lifetime_earned"] == 100


def test_premium_terminal_states_cannot_cross_over(db_session):
    owner = "google:premium-state"
    grant_sparks(db_session, owner, 100, "welcome")
    reserve_premium_sparks(db_session, owner, "op-4", "content_generation", 20)

    settle_premium_sparks(db_session, owner, "op-4")
    with pytest.raises(ValueError, match="cannot be refunded"):
        refund_premium_sparks(db_session, owner, "op-4")

    reserve_premium_sparks(db_session, owner, "op-5", "content_generation", 20)
    refund_premium_sparks(db_session, owner, "op-5")
    with pytest.raises(ValueError, match="cannot be settled"):
        settle_premium_sparks(db_session, owner, "op-5")


def test_premium_work_uses_canonical_catalog_price(db_session):
    owner = "google:premium-catalog"
    grant_sparks(db_session, owner, 100, "welcome")
    transaction = reserve_premium_work(
        db_session, owner, "op-5", "research_deep",
    )
    assert transaction.amount == cost_for("research_deep")
    assert snapshot(db_session, owner)["spark"]["balance"] == 75
