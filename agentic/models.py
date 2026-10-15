"""Data models for controlled SAGE ONE tool actions."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ActionRequest:
    """A request to execute one registered SAGE tool."""

    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    session_id: str | None = None
    task_id: str | None = None
    mission_id: str | None = None
    parent_action_id: str | None = None
    owner_key: str | None = None
    owner_authorized: bool = False
    verify: bool = True
    source: str = "agent"


@dataclass(frozen=True)
class ActionPlan:
    """Resolved tool metadata plus validated-request information."""

    tool_name: str
    capability: str | None
    permission: str
    risk: str
    handler: Any | None
    arguments: dict[str, Any]
    validation_errors: tuple[str, ...] = ()
    output_schema: dict[str, Any] | None = None
    cost_policy: dict[str, Any] | None = None
    timeout_seconds: float | None = None
    retry_policy: dict[str, Any] | None = None
    verification_policy: dict[str, Any] | None = None
    audit_policy: dict[str, Any] | None = None
    side_effect_class: str = "READ_ONLY"

    @property
    def ready(self) -> bool:
        return self.handler is not None and not self.validation_errors


@dataclass
class ActionResult:
    """Stable result returned by the Agentic Action Engine."""

    success: bool
    action_id: str | None
    tool_name: str
    status: str
    permission_allowed: bool
    permission_reason: str
    permission: str
    risk: str
    capability: str | None
    result: Any = None
    error: str | None = None
    verification_status: str = "not_requested"
    verification_reason: str | None = None
    duration_ms: int | None = None
    mission_id: str | None = None
    parent_action_id: str | None = None
    evidence: list[dict[str, Any]] = field(default_factory=list)
    event_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "action_id": self.action_id,
            "tool_name": self.tool_name,
            "status": self.status,
            "permission_allowed": self.permission_allowed,
            "permission_reason": self.permission_reason,
            "permission": self.permission,
            "risk": self.risk,
            "capability": self.capability,
            "result": self.result,
            "error": self.error,
            "verification_status": self.verification_status,
            "verification_reason": self.verification_reason,
            "duration_ms": self.duration_ms,
            "mission_id": self.mission_id,
            "parent_action_id": self.parent_action_id,
            "evidence": self.evidence,
            "event_ids": self.event_ids,
        }
