"""User-scoped persistent memory foundation.

Profile memory is intentionally separate from the legacy global Memory table so
SAGE can enforce user ownership and richer memory classification without
changing existing task/session behavior.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base, SessionLocal


MEMORY_TYPES = {
    "fact",
    "interest",
    "inference",
    "skill",
    "skill_evidence",
    "goal",
    "preference",
    "experience",
}


class ProfileMemory(Base):
    __tablename__ = "profile_memories"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    profile_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    memory_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source: Mapped[str] = mapped_column(String, default="user", nullable=False)
    confirmed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _serialize(memory: ProfileMemory) -> dict[str, Any]:
    return {
        "id": memory.id,
        "profile_id": memory.profile_id,
        "memory_type": memory.memory_type,
        "content": memory.content,
        "importance": memory.importance,
        "confidence": memory.confidence,
        "source": memory.source,
        "confirmed": bool(memory.confirmed),
        "created_at": memory.created_at.isoformat() if memory.created_at else None,
        "updated_at": memory.updated_at.isoformat() if memory.updated_at else None,
    }


def add_memory(
    *,
    profile_id: str,
    memory_type: str,
    content: str,
    importance: float = 0.5,
    confidence: float = 1.0,
    source: str = "user",
    confirmed: bool = False,
) -> dict[str, Any]:
    memory_type = memory_type.strip()
    content = content.strip()
    if memory_type not in MEMORY_TYPES:
        raise ValueError(f"Unsupported profile memory type: {memory_type}")
    if not content:
        raise ValueError("Profile memory content cannot be empty.")
    if not 0.0 <= float(confidence) <= 1.0:
        raise ValueError("Memory confidence must be between 0 and 1.")

    with SessionLocal() as db:
        memory = ProfileMemory(
            id=str(uuid.uuid4()),
            profile_id=profile_id,
            memory_type=memory_type,
            content=content,
            importance=float(importance),
            confidence=float(confidence),
            source=source,
            confirmed=1 if confirmed else 0,
            created_at=_now(),
            updated_at=_now(),
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)
        return _serialize(memory)


def list_memory(profile_id: str, limit: int = 100) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 1000))
    with SessionLocal() as db:
        rows = (
            db.query(ProfileMemory)
            .filter(ProfileMemory.profile_id == profile_id)
            .order_by(ProfileMemory.importance.desc(), ProfileMemory.created_at.desc())
            .limit(limit)
            .all()
        )
        return [_serialize(row) for row in rows]


def update_memory(memory_id: str, profile_id: str, **updates: Any) -> dict[str, Any] | None:
    allowed = {"memory_type", "content", "importance", "confidence", "source", "confirmed"}
    unknown = set(updates) - allowed
    if unknown:
        raise ValueError(f"Unsupported memory fields: {sorted(unknown)}")
    if "memory_type" in updates and updates["memory_type"] not in MEMORY_TYPES:
        raise ValueError(f"Unsupported profile memory type: {updates['memory_type']}")
    if "confidence" in updates and not 0.0 <= float(updates["confidence"]) <= 1.0:
        raise ValueError("Memory confidence must be between 0 and 1.")

    with SessionLocal() as db:
        memory = (
            db.query(ProfileMemory)
            .filter(ProfileMemory.id == memory_id, ProfileMemory.profile_id == profile_id)
            .first()
        )
        if memory is None:
            return None
        for key, value in updates.items():
            setattr(memory, key, value)
        memory.updated_at = _now()
        db.commit()
        db.refresh(memory)
        return _serialize(memory)


def delete_memory(memory_id: str, profile_id: str) -> bool:
    with SessionLocal() as db:
        memory = (
            db.query(ProfileMemory)
            .filter(ProfileMemory.id == memory_id, ProfileMemory.profile_id == profile_id)
            .first()
        )
        if memory is None:
            return False
        db.delete(memory)
        db.commit()
        return True
