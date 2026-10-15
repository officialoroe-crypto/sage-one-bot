from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


class SparkWallet(Base):
    __tablename__ = "spark_wallets"

    owner_key: Mapped[str] = mapped_column(String, primary_key=True)
    balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lifetime_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lifetime_spent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class SparkLedgerEntry(Base):
    __tablename__ = "spark_ledger"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    owner_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    reference: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class EvolutionProfile(Base):
    __tablename__ = "evolution_profiles"

    owner_key: Mapped[str] = mapped_column(String, primary_key=True)
    lifetime_achievement: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tier: Mapped[str] = mapped_column(String, default="Bronze", nullable=False)
    stage: Mapped[str] = mapped_column(String, default="LOW", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

class PremiumSparkTransaction(Base):
    """Idempotent reservation/settlement state for one premium operation."""

    __tablename__ = "premium_spark_transactions"
    __table_args__ = (
        UniqueConstraint(
            "owner_key",
            "operation_key",
            name="uq_premium_spark_operation",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    owner_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    operation_key: Mapped[str] = mapped_column(String, nullable=False)
    work_key: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="reserved", index=True)
    spend_ledger_id: Mapped[str | None] = mapped_column(String, nullable=True)
    refund_ledger_id: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    settled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
