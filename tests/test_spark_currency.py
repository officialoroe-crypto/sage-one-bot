import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.settings import settings
from database.connection import Base
from economy import currency, spend_ladder
from economy.models import EvolutionProfile, PremiumSparkTransaction, SparkLedgerEntry, SparkWallet
from economy.service import grant_sparks, snapshot


@pytest.fixture
def db_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'currency.db'}")
    Base.metadata.create_all(
        engine,
        tables=[SparkWallet.__table__, SparkLedgerEntry.__table__, EvolutionProfile.__table__, PremiumSparkTransaction.__table__],
    )
    with sessionmaker(bind=engine)() as session:
        yield session
    engine.dispose()


# ---- 1 Spark = NPR 1 ------------------------------------------------------

def test_one_spark_is_one_rupee():
    assert currency.NPR_PER_SPARK == 1
    assert currency.spark_to_npr(1) == 1
    assert currency.spark_to_npr(2_580) == 2_580
    assert currency.npr_to_spark(5_000) == 5_000
    assert currency.spark_to_npr(0) == 0


def test_negative_amounts_are_rejected():
    with pytest.raises(ValueError):
        currency.spark_to_npr(-1)
    with pytest.raises(ValueError):
        currency.npr_to_spark(-1)


def test_snapshot_reports_rupee_value(db_session):
    grant_sparks(db_session, "google:rupee-user", 120, "test grant")
    spark = snapshot(db_session, "google:rupee-user")["spark"]
    assert spark["balance"] == 120
    assert spark["npr_value"] == 120
    assert spark["currency"] == "NPR"


def test_cash_out_is_off_without_provider(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "")
    monkeypatch.setattr(settings, "PAYMENT_SECRET_KEY", "")
    monkeypatch.setattr(settings, "SPARK_CASH_OUT_ENABLED", True)
    quote = currency.cash_out_quote(500)
    assert quote["npr"] == 500
    assert quote["payout_available"] is False


def test_cash_out_needs_owner_opt_in_even_with_provider(monkeypatch):
    monkeypatch.setattr(settings, "PAYMENT_PROVIDER", "example")
    monkeypatch.setattr(settings, "PAYMENT_SECRET_KEY", "x")
    monkeypatch.setattr(settings, "SPARK_CASH_OUT_ENABLED", False)
    assert currency.cash_out_quote(500)["payout_available"] is False
    monkeypatch.setattr(settings, "SPARK_CASH_OUT_ENABLED", True)
    assert currency.cash_out_quote(500)["payout_available"] is True


# ---- Spend Trust Ladder ---------------------------------------------------

def test_nothing_earned_means_nothing_spendable():
    limit = spend_ladder.spend_limit(balance=0, lifetime_earned=0)
    assert limit.level is None
    assert limit.per_spend_limit == 0
    assert limit.requires_owner_approval is True


def test_levels_follow_lifetime_earnings():
    assert spend_ladder.level_for(0) is None
    assert spend_ladder.level_for(1)[:2] == ("Bronze", "Low")
    assert spend_ladder.level_for(10)[:2] == ("Bronze", "Mid")
    assert spend_ladder.level_for(49)[:2] == ("Bronze", "Mid")
    assert spend_ladder.level_for(50)[:2] == ("Bronze", "High")
    # Silver/Gold are undefined, so earnings above Bronze High stay at Bronze High.
    assert spend_ladder.level_for(5_000)[:2] == ("Bronze", "High")


def test_savings_lock_example_from_owner():
    # Earn 60 at the 50 level: 50 is locked as savings, only 10 can be spent at all.
    limit = spend_ladder.spend_limit(balance=60, lifetime_earned=60)
    assert limit.savings_locked == 50
    assert limit.spendable_pool == 10
    # The 10 percent rule is stricter (6), so the smaller number wins.
    assert limit.percent_cap == 6
    assert limit.per_spend_limit == 6


def test_percent_rule_on_a_hundred_earned():
    limit = spend_ladder.spend_limit(balance=100, lifetime_earned=100)
    assert limit.percent_cap == 10
    assert limit.per_spend_limit == 10


def test_percent_shrinks_as_earnings_grow():
    assert spend_ladder.percent_for(100) == 10
    assert spend_ladder.percent_for(1_000) == 5
    assert spend_ladder.percent_for(10_000) == 2
    assert spend_ladder.percent_for(50_000) == 1


def test_absolute_ceiling_applies_to_huge_wallets():
    limit = spend_ladder.spend_limit(balance=1_000_000, lifetime_earned=1_000_000)
    assert limit.per_spend_limit == spend_ladder.ABSOLUTE_CEILING


def test_spending_never_dips_into_locked_savings():
    # Balance equals the locked savings, so there is no spendable pool.
    limit = spend_ladder.spend_limit(balance=50, lifetime_earned=500)
    assert limit.spendable_pool == 0
    assert limit.per_spend_limit == 0


def test_check_spend_never_approves_on_its_own():
    ok = spend_ladder.check_spend(5, balance=100, lifetime_earned=100)
    assert ok.allowed_to_propose is True
    assert ok.requires_owner_approval is True


def test_check_spend_refuses_over_limit_zero_and_negative():
    assert spend_ladder.check_spend(11, balance=100, lifetime_earned=100).allowed_to_propose is False
    assert spend_ladder.check_spend(0, balance=100, lifetime_earned=100).allowed_to_propose is False
    assert spend_ladder.check_spend(-5, balance=100, lifetime_earned=100).allowed_to_propose is False


def test_negative_wallet_values_raise():
    with pytest.raises(ValueError):
        spend_ladder.spend_limit(balance=-1, lifetime_earned=0)


def test_ladder_is_marked_provisional_and_incomplete():
    info = spend_ladder.ladder_description()
    assert info["provisional"] is True
    assert info["ladder_complete"] is False
    assert info["owner_approval_required"] is True
