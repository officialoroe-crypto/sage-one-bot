from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


class SalesLead(Base):
    __tablename__ = "sales_leads"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    profile_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    business_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    website: Mapped[str | None] = mapped_column(Text, nullable=True)
    instagram: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    tier: Mapped[str] = mapped_column(String, nullable=False, default="hot", index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="outreach_pending", index=True)
    audit_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    intelligence_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    outreach_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class SalesActivity(Base):
    __tablename__ = "sales_activities"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    lead_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    owner_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="completed")
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
