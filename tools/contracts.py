"""Standard metadata contract for SAGE ONE registered tools."""

from dataclasses import dataclass
from typing import Any, Callable, Mapping


SIDE_EFFECT_CLASSES = {
    "READ_ONLY",
    "REVERSIBLE",
    "EXTERNAL_SIDE_EFFECT",
    "IRREVERSIBLE",
    "FINANCIAL",
    "SECURITY_SENSITIVE",
}


@dataclass(frozen=True)
class ToolContract:
    name: str
    description: str
    capability: str
    risk: str
    permission: str
    parameters: Mapping[str, Any]
    handler: Callable[..., Any]
    output_schema: Mapping[str, Any] | None = None
    cost_policy: Mapping[str, Any] | None = None
    timeout_seconds: float | None = None
    retry_policy: Mapping[str, Any] | None = None
    verification_policy: Mapping[str, Any] | None = None
    audit_policy: Mapping[str, Any] | None = None
    side_effect_class: str = "READ_ONLY"

    def __post_init__(self) -> None:
        if self.side_effect_class not in SIDE_EFFECT_CLASSES:
            raise ValueError(
                f"Unsupported side_effect_class: {self.side_effect_class}"
            )
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
