"""Deterministic outcome verification for explicit SAGE ONE criteria."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CriterionOutcome:
    criterion_id: str
    passed: bool
    evidence: str


@dataclass(frozen=True)
class OutcomeVerification:
    status: str
    passed: bool
    criteria: tuple[CriterionOutcome, ...]
    evidence: str


class OutcomeVerifier:
    """Verify explicit criteria without asking an LLM to invent proof."""

    def verify(
        self,
        *,
        criteria: list[dict[str, Any]],
        result: Any = None,
        evidence: list[dict[str, Any]] | None = None,
    ) -> OutcomeVerification:
        evidence = evidence or []
        outcomes = []

        for criterion in criteria:
            if not criterion.get("required", True):
                continue

            passed, proof = self._evaluate(
                criterion,
                result=result,
                evidence=evidence,
            )
            outcomes.append(
                CriterionOutcome(
                    criterion_id=str(criterion["id"]),
                    passed=passed,
                    evidence=proof,
                )
            )

        if not outcomes:
            return OutcomeVerification(
                status="no_explicit_criteria",
                passed=True,
                criteria=(),
                evidence="No required explicit criteria were defined.",
            )

        failed = [item for item in outcomes if not item.passed]
        if failed:
            return OutcomeVerification(
                status="failed",
                passed=False,
                criteria=tuple(outcomes),
                evidence="; ".join(
                    f"{item.criterion_id}: {item.evidence}" for item in failed
                ),
            )

        return OutcomeVerification(
            status="passed",
            passed=True,
            criteria=tuple(outcomes),
            evidence="; ".join(
                f"{item.criterion_id}: {item.evidence}" for item in outcomes
            ),
        )

    def _evaluate(
        self,
        criterion: dict[str, Any],
        *,
        result: Any,
        evidence: list[dict[str, Any]],
    ) -> tuple[bool, str]:
        kind = str(criterion.get("criterion_type", "semantic")).lower()
        expected = criterion.get("expected_value")
        description = str(criterion.get("description", "criterion"))

        if kind in {"semantic", "manual"}:
            return (
                False,
                f"{description}: requires semantic/manual verification.",
            )

        if kind in {"success", "execution_success"}:
            passed = any(item.get("success") is True for item in evidence)
            if not evidence and isinstance(result, dict):
                passed = result.get("success") is True
            return passed, (
                f"{description}: observed successful execution."
                if passed
                else f"{description}: no successful execution evidence."
            )

        if kind in {"contains", "text_contains"}:
            actual = self._text(result, evidence)
            expected_text = "" if expected is None else str(expected)
            passed = expected_text in actual
            return passed, (
                f"{description}: expected text was found."
                if passed
                else f"{description}: expected text was not found."
            )

        if kind in {"equals", "exact"}:
            actual = result
            passed = str(actual) == str(expected)
            return passed, (
                f"{description}: result matched expected value."
                if passed
                else f"{description}: result did not match expected value."
            )

        if kind in {"evidence_exists", "artifact_exists"}:
            passed = bool(evidence)
            return passed, (
                f"{description}: evidence exists."
                if passed
                else f"{description}: no evidence exists."
            )

        return (
            False,
            f"{description}: unsupported deterministic criterion type '{kind}'.",
        )

    @staticmethod
    def _text(result: Any, evidence: list[dict[str, Any]]) -> str:
        parts = [str(result)]
        for item in evidence:
            parts.append(str(item.get("result", "")))
        return "\n".join(parts)


outcome_verifier = OutcomeVerifier()
