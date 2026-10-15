from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text  # noqa: F401
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


# ============================================================
# SESSIONS
# ============================================================

class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    profile_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    owner_key: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


# ============================================================
# MESSAGES
# ============================================================

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


# ============================================================
# MEMORY
# ============================================================

class Memory(Base):
    __tablename__ = "memories"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_key: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    profile_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    memory_type: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str] = mapped_column(String, default="conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


# ============================================================
# MISSIONS
# ============================================================

class Mission(Base):
    __tablename__ = "missions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_key: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="planning", nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    current_task_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    plan_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    verification_status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ============================================================
# TASKS
# ============================================================

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    agent: Mapped[str] = mapped_column(String, default="general", nullable=False)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    parent_task_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    profile_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    project_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    owner_key: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    premium_work_key: Mapped[str | None] = mapped_column(String, nullable=True)
    mission_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    depends_on: Mapped[str | None] = mapped_column(Text, nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    verification_status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    worker_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ============================================================
# NOTIFICATIONS
# ============================================================

class Notification(Base):
    """Durable in-app notification generated by background execution."""

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_key: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    notification_type: Mapped[str] = mapped_column(String, nullable=False, default="task")
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


# ============================================================
# VERIFICATION CRITERIA
# ============================================================

class VerificationCriterion(Base):
    __tablename__ = "verification_criteria"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    mission_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    criterion_type: Mapped[str] = mapped_column(String, default="semantic", nullable=False)
    expected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    required: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


# ============================================================
# EXECUTION ATTEMPTS
# ============================================================

class ExecutionAttempt(Base):
    __tablename__ = "execution_attempts"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    mission_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String, default="running", nullable=False)
    agent: Mapped[str | None] = mapped_column(String, nullable=True)
    action_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ============================================================
# ARTIFACTS
# ============================================================

class Artifact(Base):
    __tablename__ = "artifacts"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    mission_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    artifact_type: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str | None] = mapped_column(Text, nullable=True)
    uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String, nullable=True)
    artifact_metadata: Mapped[str | None] = mapped_column("metadata", Text, nullable=True)
    verified: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


# ============================================================
# RECOVERY ATTEMPTS
# ============================================================

class RecoveryAttempt(Base):
    __tablename__ = "recovery_attempts"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    mission_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    failed_attempt_id: Mapped[str | None] = mapped_column(String, nullable=True)
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="planned", nullable=False)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ============================================================
# ACTION / EXECUTION LEDGER
# ============================================================

class ActionEvidence(Base):
    """Durable evidence produced by or attached to a controlled action."""

    __tablename__ = "action_evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    action_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    mission_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    parent_action_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    evidence_type: Mapped[str] = mapped_column(String, nullable=False, default="execution")
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


class ExecutionEvent(Base):
    """Durable lifecycle event linking actions to the broader SAGE trace."""

    __tablename__ = "execution_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    action_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    mission_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    parent_action_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String, nullable=False, default="sage")
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )


class ActionLog(Base):
    __tablename__ = "action_logs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_key: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    mission_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    parent_action_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    source: Mapped[str] = mapped_column(String, nullable=False, default="sage")
    tool: Mapped[str] = mapped_column(String, nullable=False, index=True)
    capability: Mapped[str | None] = mapped_column(String, nullable=True)
    permission: Mapped[str] = mapped_column(String, nullable=False)
    risk: Mapped[str] = mapped_column(String, nullable=False)
    arguments: Mapped[str | None] = mapped_column(Text, nullable=True)
    permission_allowed: Mapped[int] = mapped_column(Integer, nullable=False)
    permission_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="started")
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


# ============================================================
# RESEARCH RECORDS
# ============================================================

class ResearchRecord(Base):
    """Durable research report plus source/evidence/citation graph."""

    __tablename__ = "research_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_key: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="completed", index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    claim_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    provider: Mapped[str | None] = mapped_column(String, nullable=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    report_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


# ============================================================
# DURABLE AUTOMATIONS
# ============================================================

class Automation(Base):
    """Persistent schedule definition that creates normal durable tasks."""

    __tablename__ = "automations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    agent: Mapped[str] = mapped_column(String, default="general", nullable=False)
    schedule_type: Mapped[str] = mapped_column(String, default="once", nullable=False)
    run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    interval_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    run_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_runs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enabled: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False, index=True)
    last_task_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


# ============================================================
# DEVELOPER PROPOSALS
# ============================================================

class DeveloperProposal(Base):
    """Durable owner-scoped preview/apply record for Developer Mode."""

    __tablename__ = "developer_proposals"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_key: Mapped[str] = mapped_column(String, nullable=False, index=True)
    task: Mapped[str] = mapped_column(Text, nullable=False)
    workspace: Mapped[str] = mapped_column(Text, nullable=False)
    preview_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="preview", index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
