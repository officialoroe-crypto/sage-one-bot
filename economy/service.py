from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from economy.costs import cost_for
from economy.currency import spark_to_npr
from economy.models import EvolutionProfile, PremiumSparkTransaction, SparkLedgerEntry, SparkWallet
from events.service import event_store

EVOLUTION_TIERS = (
    (0, "Bronze"),
    (1_000, "Silver"),
    (5_000, "Gold"),
    (25_000, "Platinum"),
    (100_000, "Jade"),
    (250_000, "Ruby"),
    (500_000, "Sapphire"),
    (1_000_000, "Emerald"),
    (2_500_000, "Diamond Sovereign"),
    (5_000_000, "Black Opal Realm"),
    (10_000_000, "Painite Core"),
    (25_000_000, "Void Matter"),
    (100_000_000, "Californium Overlord"),
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _tier_for(achievement: int) -> tuple[str, str]:
    for index, (threshold, tier) in enumerate(reversed(EVOLUTION_TIERS)):
        if achievement >= threshold:
            stage = "HIGH" if index == 0 else "MID" if index == 1 else "LOW"
            return tier, stage
    return "Bronze", "LOW"


def evolution_progress(achievement: int) -> dict:
    current_threshold, _ = EVOLUTION_TIERS[0]
    next_tier: str | None = None
    next_threshold: int | None = None
    for index, (threshold, tier) in enumerate(EVOLUTION_TIERS):
        if achievement >= threshold:
            current_threshold = threshold
            if index + 1 < len(EVOLUTION_TIERS):
                next_threshold, next_tier = EVOLUTION_TIERS[index + 1]
        else:
            break
    if next_threshold is None:
        return {"current_threshold": current_threshold, "next_threshold": None, "next_tier": None, "ratio": 1.0}
    span = next_threshold - current_threshold
    ratio = (achievement - current_threshold) / span if span else 1.0
    return {
        "current_threshold": current_threshold,
        "next_threshold": next_threshold,
        "next_tier": next_tier,
        "ratio": max(0.0, min(1.0, ratio)),
    }


def get_wallet(db: Session, owner_key: str) -> SparkWallet:
    wallet = db.get(SparkWallet, owner_key)
    if wallet is None:
        wallet = SparkWallet(owner_key=owner_key)
        db.add(wallet)
        db.flush()
    return wallet


def get_evolution(db: Session, owner_key: str) -> EvolutionProfile:
    profile = db.get(EvolutionProfile, owner_key)
    if profile is None:
        profile = EvolutionProfile(owner_key=owner_key)
        db.add(profile)
        db.flush()
    return profile


def _existing_reference(db: Session, owner_key: str, reference: str | None) -> SparkLedgerEntry | None:
    if not reference:
        return None
    return db.scalar(
        select(SparkLedgerEntry)
        .where(
            SparkLedgerEntry.owner_key == owner_key,
            SparkLedgerEntry.reference == reference,
        )
        .order_by(SparkLedgerEntry.created_at.asc())
    )


def _validate_replay(entry: SparkLedgerEntry, amount: int, is_spend: bool) -> SparkLedgerEntry:
    expected_delta = -amount if is_spend else amount
    if entry.delta != expected_delta:
        raise ValueError(
            f"Spark reference '{entry.reference}' was already used with a different amount."
        )
    return entry


def grant_sparks(
    db: Session,
    owner_key: str,
    amount: int,
    reason: str,
    reference: str | None = None,
    metadata: dict | None = None,
    *,
    commit: bool = True,
    count_as_earned: bool = True,
) -> SparkLedgerEntry:
    if amount <= 0:
        raise ValueError("Spark grant amount must be positive")

    existing = _existing_reference(db, owner_key, reference)
    if existing is not None:
        return _validate_replay(existing, amount, is_spend=False)

    wallet = get_wallet(db, owner_key)
    now = _now()

    # Atomic increment prevents lost updates when multiple grants arrive together.
    db.execute(
        update(SparkWallet)
        .where(SparkWallet.owner_key == owner_key)
        .values(
            balance=SparkWallet.balance + amount,
            lifetime_earned=SparkWallet.lifetime_earned + (amount if count_as_earned else 0),
            updated_at=now,
        )
    )
    db.flush()
    db.refresh(wallet)

    entry = SparkLedgerEntry(
        owner_key=owner_key,
        delta=amount,
        balance_after=wallet.balance,
        reason=reason,
        reference=reference,
        metadata_json=json.dumps(metadata or {}, sort_keys=True),
    )
    db.add(entry)
    db.flush()
    if commit:
        db.commit()
        db.refresh(entry)
    event_store.emit(
        event_type="SparkGranted",
        status="completed",
        payload={
            "owner_key": owner_key,
            "amount": amount,
            "reason": reason,
            "reference": reference,
            "balance_after": entry.balance_after,
        },
        db=db,
        commit=commit,
    )
    return entry


def spend_sparks(
    db: Session,
    owner_key: str,
    amount: int,
    reason: str,
    reference: str | None = None,
    metadata: dict | None = None,
    *,
    commit: bool = True,
) -> SparkLedgerEntry:
    if amount <= 0:
        raise ValueError("Spark spend amount must be positive")

    existing = _existing_reference(db, owner_key, reference)
    if existing is not None:
        return _validate_replay(existing, amount, is_spend=True)

    wallet = get_wallet(db, owner_key)
    now = _now()

    # The balance check and debit happen in one SQL UPDATE. This avoids the
    # read/check/write race that could allow concurrent spends to overdraw.
    result = db.execute(
        update(SparkWallet)
        .where(
            SparkWallet.owner_key == owner_key,
            SparkWallet.balance >= amount,
        )
        .values(
            balance=SparkWallet.balance - amount,
            lifetime_spent=SparkWallet.lifetime_spent + amount,
            updated_at=now,
        )
    )
    if result.rowcount != 1:
        db.rollback()
        raise ValueError("Insufficient SAGE Spark balance")

    db.flush()
    db.refresh(wallet)

    entry = SparkLedgerEntry(
        owner_key=owner_key,
        delta=-amount,
        balance_after=wallet.balance,
        reason=reason,
        reference=reference,
        metadata_json=json.dumps(metadata or {}, sort_keys=True),
    )
    db.add(entry)
    db.flush()
    if commit:
        db.commit()
        db.refresh(entry)
    event_store.emit(
        event_type="SparkSpent",
        status="completed",
        payload={
            "owner_key": owner_key,
            "amount": amount,
            "reason": reason,
            "reference": reference,
            "balance_after": entry.balance_after,
        },
        db=db,
        commit=commit,
    )
    return entry



def _premium_reference(operation_key: str) -> str:
    return f"premium:{operation_key}"


def _premium_refund_reference(operation_key: str) -> str:
    return f"premium-refund:{operation_key}"


def reserve_premium_sparks(
    db: Session,
    owner_key: str,
    operation_key: str,
    work_key: str,
    amount: int,
    metadata: dict | None = None,
) -> PremiumSparkTransaction:
    """Atomically reserve Spark for one premium operation."""
    if not operation_key.strip():
        raise ValueError("Premium operation key is required")
    if amount <= 0:
        raise ValueError("Premium reservation amount must be positive")

    existing = db.scalar(
        select(PremiumSparkTransaction).where(
            PremiumSparkTransaction.owner_key == owner_key,
            PremiumSparkTransaction.operation_key == operation_key,
        )
    )
    if existing is not None:
        if existing.work_key != work_key or existing.amount != amount:
            raise ValueError("Premium operation key was already used with different work or amount")
        return existing

    transaction = PremiumSparkTransaction(
        owner_key=owner_key,
        operation_key=operation_key,
        work_key=work_key,
        amount=amount,
        status="reserved",
        metadata_json=json.dumps(metadata or {}, sort_keys=True),
    )
    db.add(transaction)
    try:
        db.flush()
        ledger = spend_sparks(
            db, owner_key, amount,
            reason=f"Premium reserve: {work_key}",
            reference=_premium_reference(operation_key),
            metadata={"operation_key": operation_key, "work_key": work_key},
            commit=False,
        )
        transaction.spend_ledger_id = ledger.id
        db.commit()
        db.refresh(transaction)
        return transaction
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(PremiumSparkTransaction).where(
                PremiumSparkTransaction.owner_key == owner_key,
                PremiumSparkTransaction.operation_key == operation_key,
            )
        )
        if existing is None:
            raise
        if existing.work_key != work_key or existing.amount != amount:
            raise ValueError("Premium operation key was already used with different work or amount")
        return existing
    except Exception:
        db.rollback()
        raise



def reserve_premium_work(
    db: Session,
    owner_key: str,
    operation_key: str,
    work_key: str,
    metadata: dict | None = None,
) -> PremiumSparkTransaction:
    """Reserve the catalog price for a named premium work type."""
    return reserve_premium_sparks(
        db,
        owner_key,
        operation_key,
        work_key,
        cost_for(work_key),
        metadata,
    )


def settle_premium_sparks(
    db: Session,
    owner_key: str,
    operation_key: str,
) -> PremiumSparkTransaction:
    transaction = db.scalar(
        select(PremiumSparkTransaction).where(
            PremiumSparkTransaction.owner_key == owner_key,
            PremiumSparkTransaction.operation_key == operation_key,
        )
    )
    if transaction is None:
        raise ValueError("Premium operation reservation was not found")
    if transaction.status == "settled":
        return transaction
    if transaction.status == "refunded":
        raise ValueError("A refunded premium operation cannot be settled")
    if transaction.status != "reserved":
        raise ValueError(f"Premium operation cannot settle from status: {transaction.status}")

    transaction.status = "settled"
    transaction.settled_at = _now()
    db.commit()
    db.refresh(transaction)
    return transaction


def refund_premium_sparks(
    db: Session,
    owner_key: str,
    operation_key: str,
    reason: str = "Premium operation failed",
) -> PremiumSparkTransaction:
    transaction = db.scalar(
        select(PremiumSparkTransaction).where(
            PremiumSparkTransaction.owner_key == owner_key,
            PremiumSparkTransaction.operation_key == operation_key,
        )
    )
    if transaction is None:
        raise ValueError("Premium operation reservation was not found")
    if transaction.status == "refunded":
        return transaction
    if transaction.status == "settled":
        raise ValueError("A settled premium operation cannot be refunded")
    if transaction.status != "reserved":
        raise ValueError(f"Premium operation cannot refund from status: {transaction.status}")

    try:
        ledger = grant_sparks(
            db, owner_key, transaction.amount,
            reason=reason,
            reference=_premium_refund_reference(operation_key),
            metadata={"operation_key": operation_key, "work_key": transaction.work_key},
            commit=False,
            count_as_earned=False,
        )
        transaction.refund_ledger_id = ledger.id
        transaction.status = "refunded"
        transaction.refunded_at = _now()
        db.commit()
        db.refresh(transaction)
        return transaction
    except Exception:
        db.rollback()
        raise


def premium_transaction(
    db: Session,
    owner_key: str,
    operation_key: str,
) -> PremiumSparkTransaction | None:
    return db.scalar(
        select(PremiumSparkTransaction).where(
            PremiumSparkTransaction.owner_key == owner_key,
            PremiumSparkTransaction.operation_key == operation_key,
        )
    )

def record_achievement(
    db: Session,
    owner_key: str,
    amount: int,
    reason: str,
    *,
    commit: bool = True,
) -> EvolutionProfile:
    if amount <= 0:
        raise ValueError("Achievement amount must be positive")
    profile = get_evolution(db, owner_key)
    profile.lifetime_achievement += amount
    profile.tier, profile.stage = _tier_for(profile.lifetime_achievement)
    profile.updated_at = _now()
    if commit:
        db.commit()
        db.refresh(profile)
    event_store.emit(
        event_type="EvolutionAchievementRecorded",
        status="completed",
        payload={
            "owner_key": owner_key,
            "amount": amount,
            "reason": reason,
            "lifetime_achievement": profile.lifetime_achievement,
            "tier": profile.tier,
            "stage": profile.stage,
        },
        db=db,
        commit=commit,
    )
    return profile


def snapshot(db: Session, owner_key: str) -> dict:
    wallet = get_wallet(db, owner_key)
    evolution = get_evolution(db, owner_key)
    entries = db.scalars(
        select(SparkLedgerEntry)
        .where(SparkLedgerEntry.owner_key == owner_key)
        .order_by(SparkLedgerEntry.created_at.desc())
        .limit(50)
    ).all()
    return {
        "spark": {
            "name": "SAGE Spark",
            "balance": wallet.balance,
            "lifetime_earned": wallet.lifetime_earned,
            "lifetime_spent": wallet.lifetime_spent,
            "npr_value": spark_to_npr(wallet.balance),
            "currency": "NPR",
            "rule": "1 Spark = NPR 1",
        },
        "evolution": {
            "lifetime_achievement": evolution.lifetime_achievement,
            "tier": evolution.tier,
            "stage": evolution.stage,
            "progress": evolution_progress(evolution.lifetime_achievement),
        },
        "ledger": [
            {
                "id": entry.id,
                "delta": entry.delta,
                "balance_after": entry.balance_after,
                "reason": entry.reason,
                "reference": entry.reference,
                "created_at": entry.created_at.isoformat(),
            }
            for entry in entries
        ],
    }


def evolution_simulation(db: Session, owner_key: str, target_achievement: int, duration_ms: int = 3000) -> dict:
    if target_achievement < 0:
        raise ValueError("Simulation achievement cannot be negative")
    duration_ms = max(500, min(int(duration_ms), 30_000))
    profile = get_evolution(db, owner_key)
    start = profile.lifetime_achievement
    target_tier, target_stage = _tier_for(target_achievement)
    start_tier, start_stage = _tier_for(start)
    low, high = sorted((start, target_achievement))
    milestones = [
        {"achievement": threshold, "tier": tier}
        for threshold, tier in EVOLUTION_TIERS
        if low < threshold <= high
    ]
    if target_achievement < start:
        milestones = list(reversed(milestones))

    return {
        "simulation": True,
        "mutated": False,
        "duration_ms": duration_ms,
        "direction": "up" if target_achievement >= start else "down",
        "from": {
            "lifetime_achievement": start,
            "tier": start_tier,
            "stage": start_stage,
            "progress": evolution_progress(start),
        },
        "to": {
            "lifetime_achievement": target_achievement,
            "tier": target_tier,
            "stage": target_stage,
            "progress": evolution_progress(target_achievement),
        },
        "milestones": milestones,
    }
