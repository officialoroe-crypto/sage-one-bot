"""Spend Trust Ladder: how much SAGE may *propose* to spend.

This is the Money Upgrade path of the locked Evolution system ("Work -> Earn ->
Economic Achievement -> System Upgrade"). It controls spending authority only;
it does not change the skill-based Evolution rank or its visuals.

Rules (owner design, 2026-10-11):
  * SAGE starts with nothing. It earns first; the owner never funds it.
  * Levels are Bronze/Silver/Gold, each with Low/Mid/High. A level is reached
    when lifetime earnings reach that level's threshold.
  * Savings lock: earnings up to the current level's threshold are locked as
    savings and are never spendable. Only the surplus above it is spendable.
  * Percentage rule: a single spend may be at most a percentage of lifetime
    earnings; the percentage shrinks as earnings grow.
  * Absolute ceiling: no single spend may exceed the ceiling, however rich.
  * The owner approves every spend. Nothing here ever returns "approved".
    A passing check only means the amount may be put in front of the owner.
  * Fail closed: unknown levels, negative or zero amounts are refused.

ALL NUMBERS ARE PROVISIONAL until the owner confirms them. The owner first
described the Bronze caps and the 10 / 5 / 2 percent bands in dollars; they are
read here as Spark. Silver and Gold are not defined yet, so the ladder stops at
Bronze High and the limits stay at Bronze High until the owner sets them.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

# (name, sublevel, lifetime-earnings threshold in Spark). Ordered low to high.
LADDER: tuple[tuple[str, str, int], ...] = (
    ("Bronze", "Low", 1),
    ("Bronze", "Mid", 10),
    ("Bronze", "High", 50),
    # Silver and Gold: owner has not set values yet. Add them here when decided.
)
LADDER_COMPLETE = False

# (up to this lifetime-earnings amount, max share of earnings per single spend in %)
PERCENT_BANDS: tuple[tuple[int, int], ...] = (
    (100, 10),
    (1_000, 5),
    (10_000, 2),
)
PERCENT_ABOVE_BANDS = 1
ABSOLUTE_CEILING = 200  # owner said 200 to 500; the safer low end is used until confirmed


@dataclass(frozen=True)
class SpendLimit:
    level: str | None
    savings_locked: int
    spendable_pool: int
    percent_cap: int
    per_spend_limit: int
    requires_owner_approval: bool
    ladder_complete: bool
    note: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class SpendCheck:
    allowed_to_propose: bool
    requires_owner_approval: bool
    limit: int
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def level_for(lifetime_earned: int) -> tuple[str, str, int] | None:
    """Highest ladder level reached by lifetime earnings, or None if none yet."""
    reached = None
    for name, sublevel, threshold in LADDER:
        if lifetime_earned >= threshold:
            reached = (name, sublevel, threshold)
    return reached


def percent_for(lifetime_earned: int) -> int:
    for upper, percent in PERCENT_BANDS:
        if lifetime_earned <= upper:
            return percent
    return PERCENT_ABOVE_BANDS


def spend_limit(balance: int, lifetime_earned: int) -> SpendLimit:
    """How much one spend proposal may be, given the current wallet."""
    if balance < 0 or lifetime_earned < 0:
        raise ValueError("Balance and lifetime earnings cannot be negative")
    reached = level_for(lifetime_earned)
    if reached is None:
        return SpendLimit(
            level=None, savings_locked=0, spendable_pool=0, percent_cap=0,
            per_spend_limit=0, requires_owner_approval=True,
            ladder_complete=LADDER_COMPLETE,
            note="Nothing earned yet, so nothing is spendable.",
        )
    name, sublevel, threshold = reached
    pool = max(0, balance - threshold)
    percent_cap = (lifetime_earned * percent_for(lifetime_earned)) // 100
    per_spend = min(pool, percent_cap, ABSOLUTE_CEILING)
    return SpendLimit(
        level=f"{name} {sublevel}",
        savings_locked=min(balance, threshold),
        spendable_pool=pool,
        percent_cap=percent_cap,
        per_spend_limit=per_spend,
        requires_owner_approval=True,
        ladder_complete=LADDER_COMPLETE,
        note=(
            "Every spend still needs the owner's approval."
            if LADDER_COMPLETE
            else "Silver and Gold limits are not set yet; limits stay at the highest defined level."
        ),
    )


def check_spend(amount: int, balance: int, lifetime_earned: int) -> SpendCheck:
    """May this amount be proposed to the owner? Never returns an approval."""
    limit = spend_limit(balance, lifetime_earned)
    if amount <= 0:
        return SpendCheck(False, True, limit.per_spend_limit, "Spend amount must be positive.")
    if amount > limit.per_spend_limit:
        return SpendCheck(
            False, True, limit.per_spend_limit,
            f"Amount is above the current limit of {limit.per_spend_limit} Spark per spend.",
        )
    return SpendCheck(True, True, limit.per_spend_limit, "Within limit. Owner approval is still required.")


def ladder_description() -> dict:
    return {
        "levels": [
            {"name": name, "sublevel": sublevel, "threshold": threshold}
            for name, sublevel, threshold in LADDER
        ],
        "ladder_complete": LADDER_COMPLETE,
        "percent_bands": [{"up_to": up, "percent": pct} for up, pct in PERCENT_BANDS]
        + [{"up_to": None, "percent": PERCENT_ABOVE_BANDS}],
        "absolute_ceiling": ABSOLUTE_CEILING,
        "owner_approval_required": True,
        "provisional": True,
    }
