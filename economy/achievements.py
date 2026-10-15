from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from database.connection import Base
from economy.service import record_achievement


VERIFIED_TASK_ACHIEVEMENT = 100


class VerifiedAchievementEvent(Base):
    """Immutable-ish owner-scoped record of a verified achievement outcome."""

    __tablename__ = "verified_achievement_events"
    __table_args__ = (
        UniqueConstraint(
            "owner_key",
            "source_type",
            "source_id",
            name="uq_verified_achievement_source",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    owner_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    verification_status: Mapped[str] = mapped_column(String, nullable=False, default="verified")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


def record_verified_achievement(
    db: Session,
    owner_key: str,
    amount: int,
    reason: str,
    source_type: str,
    source_id: str,
    evidence: dict,
    *,
    commit: bool = True,
) -> tuple[VerifiedAchievementEvent, bool]:
    """Record one verified achievement exactly once and atomically."""

    if amount <= 0:
        raise ValueError("Achievement amount must be positive")
    if not source_type.strip() or not source_id.strip():
        raise ValueError("Verified achievements require a source type and source ID")
    if not isinstance(evidence, dict) or not evidence:
        raise ValueError("Verified achievements require evidence")

    source_type = source_type.strip()
    source_id = source_id.strip()
    existing = db.scalar(
        select(VerifiedAchievementEvent).where(
            VerifiedAchievementEvent.owner_key == owner_key,
            VerifiedAchievementEvent.source_type == source_type,
            VerifiedAchievementEvent.source_id == source_id,
        )
    )
    if existing is not None:
        return existing, False

    event = VerifiedAchievementEvent(
        owner_key=owner_key,
        source_type=source_type,
        source_id=source_id,
        amount=amount,
        reason=reason.strip(),
        evidence_json=json.dumps(evidence, ensure_ascii=False, sort_keys=True),
        verification_status="verified",
    )
    db.add(event)

    try:
        # Flush only: keep the event and Evolution mutation in one transaction.
        db.flush()
        record_achievement(db, owner_key, amount, reason, commit=False)
        if commit:
            db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(VerifiedAchievementEvent).where(
                VerifiedAchievementEvent.owner_key == owner_key,
                VerifiedAchievementEvent.source_type == source_type,
                VerifiedAchievementEvent.source_id == source_id,
            )
        )
        if existing is None:
            raise
        return existing, False
    except Exception:
        # Any failure after the event is staged must roll back both the event
        # and Evolution mutation before the caller can reuse this session.
        db.rollback()
        raise

    if commit:
        db.refresh(event)
    return event, True
