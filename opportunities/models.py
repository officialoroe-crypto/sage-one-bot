from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class JobPosting(Base):
    __tablename__ = "job_postings"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    employer_profile_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    employer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    company: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    employment_type: Mapped[str] = mapped_column(String(40), nullable=False, default="full_time")
    salary_min_npr: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max_npr: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False, index=True)


class JobApplication(Base):
    __tablename__ = "job_applications"
    __table_args__ = (
        UniqueConstraint("job_id", "applicant_profile_id", name="uq_job_applicant"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    applicant_profile_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    applicant_name: Mapped[str] = mapped_column(String(200), nullable=False)
    cover_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="submitted")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False, index=True)


class MarketplaceListing(Base):
    __tablename__ = "marketplace_listings"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    seller_profile_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    seller_name: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    price_npr: Mapped[float] = mapped_column(Float, nullable=False)
    item_condition: Mapped[str] = mapped_column(String(30), nullable=False, default="used")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False, index=True)


class MarketplaceInquiry(Base):
    __tablename__ = "marketplace_inquiries"
    __table_args__ = (
        UniqueConstraint("listing_id", "buyer_profile_id", name="uq_listing_buyer"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    listing_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    buyer_profile_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    buyer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False, index=True)
