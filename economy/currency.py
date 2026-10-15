"""SAGE Spark currency rule.

LOCKED OWNER RULE (2026-10-11): 1 SAGE Spark = 1 Nepali Rupee (NPR 1).

This module only defines the exchange rule and cash-out *quotes*. It never
moves money. Paying real rupees out requires a configured payment provider and
an explicit owner opt-in (``SAGE_SPARK_CASH_OUT_ENABLED``). Until both exist,
every quote reports ``payout_available = False`` so the UI cannot pretend that
cash-out works.
"""

from __future__ import annotations

from config.settings import settings

CURRENCY_CODE = "NPR"
NPR_PER_SPARK = 1  # locked owner rule: 1 Spark = NPR 1


def spark_to_npr(spark: int) -> int:
    """Rupee value of a Spark amount."""
    if spark < 0:
        raise ValueError("Spark amount cannot be negative")
    return spark * NPR_PER_SPARK


def npr_to_spark(npr: int) -> int:
    """Whole Spark that a rupee amount buys. Never rounds in the user's favour."""
    if npr < 0:
        raise ValueError("NPR amount cannot be negative")
    return npr // NPR_PER_SPARK


def cash_out_available() -> tuple[bool, str]:
    """Whether real-rupee payout can happen right now, and why not if it can't."""
    if not (settings.PAYMENT_PROVIDER and settings.PAYMENT_SECRET_KEY):
        return False, "No payment provider is configured, so Spark cannot be paid out as rupees yet."
    if not settings.SPARK_CASH_OUT_ENABLED:
        return False, "Cash-out is switched off until the owner enables it after the legal review."
    return True, "Cash-out is enabled."


def cash_out_quote(spark: int) -> dict:
    """Quote what a Spark amount is worth in rupees. Does not move money."""
    npr = spark_to_npr(spark)
    available, reason = cash_out_available()
    return {
        "spark": spark,
        "npr": npr,
        "currency": CURRENCY_CODE,
        "rate": {"npr_per_spark": NPR_PER_SPARK},
        "payout_available": available,
        "message": reason,
    }


def currency_info() -> dict:
    available, reason = cash_out_available()
    return {
        "name": "SAGE Spark",
        "currency": CURRENCY_CODE,
        "npr_per_spark": NPR_PER_SPARK,
        "rule": "1 Spark = NPR 1",
        "payout_available": available,
        "payout_message": reason,
    }
