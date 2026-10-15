"""Execution-level verification for SAGE ONE actions.

This layer verifies execution integrity, not business truth. A successful
handler return is evidence that the action executed without an exception.
Tools can explicitly report {"success": false} to mark execution failure.
Deeper semantic verification can be added later without weakening this gate.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VerificationOutcome:
    status: str
    reason: str
    evidence: str | None = None


class VerificationEngine:
    """Perform conservative post-execution verification."""

    def verify_execution(
        self,
        *,
        success: bool,
        result: Any = None,
        error: str | None = None,
    ) -> VerificationOutcome:
        if not success:
            return VerificationOutcome(
                status="failed",
                reason=error or "Action execution failed.",
                evidence="handler_exception_or_execution_failure",
            )

        if isinstance(result, dict) and result.get("success") is False:
            tool_error = result.get("error") or "Tool reported success=false."
            return VerificationOutcome(
                status="failed",
                reason=str(tool_error),
                evidence="tool_reported_failure",
            )

        return VerificationOutcome(
            status="passed",
            reason="Action handler completed without reporting failure.",
            evidence="handler_returned_normally",
        )
