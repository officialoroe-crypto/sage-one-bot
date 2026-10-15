from datetime import datetime, timezone

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LessonProgress(Base):
    """A learner's durable completion record for a catalog lesson."""

    __tablename__ = "learning_lesson_progress"
    __table_args__ = (
        UniqueConstraint("profile_id", "lesson_id", name="uq_learning_profile_lesson"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    profile_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    lesson_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=_utc_now, nullable=False)
