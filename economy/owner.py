"""Owner-only development controls for SAGE internal economy and evolution."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from database.connection import Base
from economy.models import EvolutionProfile, SparkWallet


class OwnerAuditEvent(Base):
    __tablename__ = "owner_audit_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    owner_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String, nullable=False, index=True)
    target: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    details_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


def record_owner_audit(
    db: Session,
    owner_key: str,
    action: str,
    target: str,
    reason: str,
    amount: int | None = None,
    details: dict | None = None,
    *,
    commit: bool = True,
) -> OwnerAuditEvent:
    event = OwnerAuditEvent(
        owner_key=owner_key,
        action=action.strip(),
        target=target.strip(),
        amount=amount,
        reason=reason.strip(),
        details_json=json.dumps(details or {}, ensure_ascii=False, sort_keys=True),
    )
    db.add(event)
    if commit:
        db.commit()
        db.refresh(event)
    return event


def owner_audit(db: Session, owner_key: str, limit: int = 100) -> list[dict]:
    rows = db.scalars(
        select(OwnerAuditEvent)
        .where(OwnerAuditEvent.owner_key == owner_key)
        .order_by(OwnerAuditEvent.created_at.desc())
        .limit(max(1, min(limit, 500)))
    ).all()
    return [
        {
            "id": row.id,
            "action": row.action,
            "target": row.target,
            "amount": row.amount,
            "reason": row.reason,
            "details": json.loads(row.details_json or "{}"),
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


def reset_spark(db: Session, owner_key: str, reason: str) -> SparkWallet:
    wallet = db.get(SparkWallet, owner_key)
    if wallet is None:
        wallet = SparkWallet(owner_key=owner_key)
        db.add(wallet)
    wallet.balance = 0
    wallet.lifetime_earned = 0
    wallet.lifetime_spent = 0
    wallet.updated_at = datetime.now(timezone.utc)
    record_owner_audit(db, owner_key, "reset", "spark", reason, commit=False)
    db.commit()
    db.refresh(wallet)
    return wallet


def set_spark(db: Session, owner_key: str, amount: int, reason: str) -> SparkWallet:
    wallet = db.get(SparkWallet, owner_key)
    if wallet is None:
        wallet = SparkWallet(owner_key=owner_key)
        db.add(wallet)
    wallet.balance = amount
    wallet.updated_at = datetime.now(timezone.utc)
    record_owner_audit(db, owner_key, "set", "spark", reason, amount=amount, commit=False)
    db.commit()
    db.refresh(wallet)
    return wallet


def reset_evolution(db: Session, owner_key: str, reason: str) -> EvolutionProfile:
    profile = db.get(EvolutionProfile, owner_key)
    if profile is None:
        profile = EvolutionProfile(owner_key=owner_key)
        db.add(profile)
    profile.lifetime_achievement = 0
    profile.tier = "Bronze"
    profile.stage = "LOW"
    profile.updated_at = datetime.now(timezone.utc)
    record_owner_audit(db, owner_key, "reset", "evolution", reason, commit=False)
    db.commit()
    db.refresh(profile)
    return profile


def set_evolution(
    db: Session,
    owner_key: str,
    achievement: int,
    tier: str,
    stage: str,
    reason: str,
) -> EvolutionProfile:
    tier = tier.strip()
    stage = stage.strip()
    profile = db.get(EvolutionProfile, owner_key)
    if profile is None:
        profile = EvolutionProfile(owner_key=owner_key)
        db.add(profile)
    profile.lifetime_achievement = achievement
    profile.tier = tier
    profile.stage = stage
    profile.updated_at = datetime.now(timezone.utc)
    record_owner_audit(
        db,
        owner_key,
        "set",
        "evolution",
        reason,
        amount=achievement,
        details={"tier": tier, "stage": stage},
        commit=False,
    )
    db.commit()
    db.refresh(profile)
    return profile
