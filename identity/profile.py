"""Shared SAGE ONE user profile persistence.

Authentication providers own identity proof. This module stores the minimum
profile/onboarding state SAGE needs after authentication has succeeded.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base, SessionLocal


class UserProfile(Base):
    __tablename__ = "user_profiles"
    __table_args__ = (
        UniqueConstraint("auth_provider", "auth_subject", name="uq_user_auth_identity"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    auth_provider: Mapped[str] = mapped_column(String, nullable=False, index=True)
    auth_subject: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    phone_verified: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    phone_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    basic_info_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    help_intent: Mapped[str | None] = mapped_column(Text, nullable=True)
    capabilities_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    memory_consent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    onboarding_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _json_load(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except Exception:
        return fallback


def serialize_profile(profile: UserProfile) -> dict[str, Any]:
    return {
        "id": profile.id,
        "auth_provider": profile.auth_provider,
        "auth_subject": profile.auth_subject,
        "email": profile.email,
        "name": profile.name,
        "phone": profile.phone,
        "phone_verified": bool(profile.phone_verified),
        "phone_verified_at": profile.phone_verified_at.isoformat() if profile.phone_verified_at else None,
        "address": profile.address,
        "age": profile.age,
        "basic_info": _json_load(profile.basic_info_json, {}),
        "help_intent": profile.help_intent,
        "capabilities": _json_load(profile.capabilities_json, []),
        "memory_consent": bool(profile.memory_consent),
        "onboarding_completed": bool(profile.onboarding_completed),
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


def get_profile(auth_provider: str, auth_subject: str) -> dict[str, Any] | None:
    with SessionLocal() as db:
        profile = (
            db.query(UserProfile)
            .filter(
                UserProfile.auth_provider == auth_provider,
                UserProfile.auth_subject == auth_subject,
            )
            .first()
        )
        return serialize_profile(profile) if profile else None


def upsert_profile(
    *,
    auth_provider: str,
    auth_subject: str,
    email: str | None = None,
    name: str | None = None,
    phone: str | None = None,
    address: str | None = None,
    age: int | None = None,
    basic_info: dict[str, Any] | None = None,
    help_intent: str | None = None,
    capabilities: list[str] | None = None,
    memory_consent: bool | None = None,
) -> dict[str, Any]:
    """Create or update a profile after trusted authentication claims exist."""
    if not auth_provider.strip() or not auth_subject.strip():
        raise ValueError("Authenticated identity is required.")
    if age is not None and not 1 <= int(age) <= 120:
        raise ValueError("Age must be between 1 and 120.")

    with SessionLocal() as db:
        profile = (
            db.query(UserProfile)
            .filter(
                UserProfile.auth_provider == auth_provider,
                UserProfile.auth_subject == auth_subject,
            )
            .first()
        )

        if profile is None:
            profile = UserProfile(
                id=str(uuid.uuid4()),
                auth_provider=auth_provider,
                auth_subject=auth_subject,
                created_at=_now(),
                updated_at=_now(),
            )
            db.add(profile)

        if email is not None:
            profile.email = email
        if name is not None:
            profile.name = name
        if phone is not None:
            profile.phone = phone
        if address is not None:
            profile.address = address
        if age is not None:
            profile.age = int(age)
        if basic_info is not None:
            profile.basic_info_json = json.dumps(basic_info, ensure_ascii=False, default=str)
        if help_intent is not None:
            profile.help_intent = help_intent
        if capabilities is not None:
            profile.capabilities_json = json.dumps(sorted(set(capabilities)), ensure_ascii=False)
        if memory_consent is not None:
            profile.memory_consent = 1 if memory_consent else 0

        profile.updated_at = _now()
        db.commit()
        db.refresh(profile)
        return serialize_profile(profile)


def mark_phone_verified(auth_provider: str, auth_subject: str) -> dict[str, Any]:
    with SessionLocal() as db:
        profile = (
            db.query(UserProfile)
            .filter(
                UserProfile.auth_provider == auth_provider,
                UserProfile.auth_subject == auth_subject,
            )
            .first()
        )
        if profile is None:
            raise ValueError("Profile not found.")

        now = _now()
        profile.phone_verified = 1
        profile.phone_verified_at = now
        profile.updated_at = now
        db.commit()
        db.refresh(profile)
        return serialize_profile(profile)
