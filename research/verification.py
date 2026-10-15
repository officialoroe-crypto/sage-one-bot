from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import re


VERIFIED_THRESHOLD = 0.80
PARTIAL_THRESHOLD = 0.50


@dataclass
class VerificationResult:
    status: str
    score: float
    reason: str
    supporting_evidence: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)


class ResearchVerifier:
    """
    Deterministic first-pass verifier for SAGE ONE research claims.

    The verifier does not trust the model's confidence score.
    It checks whether a claim has traceable evidence and whether
    the evidence contains language that supports or contradicts it.
    """

    name = "research_verifier"

    def _get(self, obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)

        return getattr(obj, key, default)

    def _clean(self, value: Any) -> str:
        if value is None:
            return ""

        return re.sub(r"\s+", " ", str(value)).strip()

    def _tokens(self, text: str) -> set[str]:
        words = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]{2,}", text.lower())

        stopwords = {
            "the",
            "and",
            "that",
            "this",
            "with",
            "from",
            "into",
            "have",
            "has",
            "been",
            "were",
            "will",
            "would",
            "could",
            "should",
            "their",
            "there",
            "they",
            "them",
            "than",
            "then",
            "about",
            "which",
            "while",
            "where",
            "when",
            "what",
            "also",
            "more",
            "most",
            "some",
            "such",
            "only",
            "over",
            "under",
            "after",
            "before",
            "between",
            "through",
            "using",
            "used",
            "into",
        }

        return {
            token
            for token in words
            if token not in stopwords
        }

    def _evidence_text(self, evidence: Any) -> str:
        parts = [
            self._get(evidence, "title", ""),
            self._get(evidence, "snippet", ""),
            self._get(evidence, "content", ""),
        ]

        return self._clean(" ".join(str(part) for part in parts if part))

    def _evidence_id(self, evidence: Any) -> str:
        return self._clean(
            self._get(
                evidence,
                "evidence_id",
                self._get(
                    evidence,
                    "source_id",
                    self._get(evidence, "id", ""),
                ),
            )
        )

    def _claim_support_score(
        self,
        claim: str,
        evidence_text: str,
    ) -> float:
        claim_tokens = self._tokens(claim)
        evidence_tokens = self._tokens(evidence_text)

        if not claim_tokens or not evidence_tokens:
            return 0.0

        overlap = claim_tokens.intersection(evidence_tokens)

        coverage = len(overlap) / len(claim_tokens)

        # Stronger signal when the claim contains distinctive
        # numbers or named entities also present in the evidence.
        claim_numbers = set(re.findall(r"\b\d+(?:\.\d+)?%?\b", claim))
        evidence_numbers = set(
            re.findall(r"\b\d+(?:\.\d+)?%?\b", evidence_text)
        )

        number_bonus = 0.0

        if claim_numbers:
            matching_numbers = claim_numbers.intersection(evidence_numbers)

            if matching_numbers:
                number_bonus = min(
                    0.25,
                    0.25
                    * (
                        len(matching_numbers)
                        / len(claim_numbers)
                    ),
                )
            else:
                # Numerical claims without matching numerical
                # evidence deserve a substantial penalty.
                number_bonus = -0.20

        score = coverage + number_bonus

        return max(0.0, min(1.0, score))

    def _looks_contradictory(
        self,
        claim: str,
        evidence_text: str,
    ) -> bool:
        evidence_lower = evidence_text.lower()

        contradiction_patterns = [
            r"\bnot\b",
            r"\bno evidence\b",
            r"\bdisputes?\b",
            r"\bdisputed\b",
            r"\bcontradicts?\b",
            r"\bcontradicted\b",
            r"\bincorrect\b",
            r"\bfalse\b",
            r"\bunverified\b",
            r"\bunable to confirm\b",
            r"\bfailed to confirm\b",
            r"\bdenied\b",
            r"\bdoes not support\b",
            r"\bnot supported\b",
        ]

        if not any(
            re.search(pattern, evidence_lower)
            for pattern in contradiction_patterns
        ):
            return False

        # Avoid treating generic "not" statements as contradictions
        # unless the evidence also shares meaningful claim terms.
        claim_tokens = self._tokens(claim)
        evidence_tokens = self._tokens(evidence_text)

        overlap = claim_tokens.intersection(evidence_tokens)

        return len(overlap) >= max(2, min(5, len(claim_tokens) // 3))

    def verify_claim(
        self,
        claim: Any,
        evidence: list[Any],
    ) -> VerificationResult:
        claim_text = self._clean(
            self._get(claim, "claim", "")
        )

        if not claim_text:
            return VerificationResult(
                status="UNVERIFIED",
                score=0.0,
                reason="Claim is empty.",
            )

        supporting: list[str] = []
        contradicting: list[str] = []

        best_support_score = 0.0

        for item in evidence:
            evidence_id = self._evidence_id(item)
            evidence_text = self._evidence_text(item)

            if not evidence_id or not evidence_text:
                continue

            score = self._claim_support_score(
                claim_text,
                evidence_text,
            )

            if score > best_support_score:
                best_support_score = score

            if score >= PARTIAL_THRESHOLD:
                supporting.append(evidence_id)

            if self._looks_contradictory(
                claim_text,
                evidence_text,
            ):
                contradicting.append(evidence_id)

        if contradicting and not supporting:
            return VerificationResult(
                status="CONTRADICTED",
                score=0.0,
                reason="Available evidence contains contradictory signals.",
                supporting_evidence=supporting,
                contradicting_evidence=contradicting,
            )

        if not supporting:
            return VerificationResult(
                status="UNVERIFIED",
                score=best_support_score,
                reason="No sufficiently matching evidence was found.",
                supporting_evidence=[],
                contradicting_evidence=contradicting,
            )

        if contradicting:
            return VerificationResult(
                status="PARTIALLY_VERIFIED",
                score=min(best_support_score, 0.65),
                reason="Evidence supports the claim but contradictory signals were also found.",
                supporting_evidence=supporting,
                contradicting_evidence=contradicting,
            )

        if best_support_score >= VERIFIED_THRESHOLD:
            return VerificationResult(
                status="VERIFIED",
                score=best_support_score,
                reason="Claim has strong lexical and numerical alignment with supplied evidence.",
                supporting_evidence=supporting,
                contradicting_evidence=[],
            )

        return VerificationResult(
            status="PARTIALLY_VERIFIED",
            score=best_support_score,
            reason="Claim has some evidence alignment but not enough for full verification.",
            supporting_evidence=supporting,
            contradicting_evidence=[],
        )

    def verify_report(
        self,
        report: Any,
        evidence: list[Any],
    ) -> Any:
        claims = self._get(report, "claims", [])

        verified_claims = []

        for claim in claims or []:
            result = self.verify_claim(
                claim,
                evidence,
            )

            if isinstance(claim, dict):
                updated = dict(claim)
                updated["status"] = result.status
                updated["confidence_score"] = round(
                    result.score,
                    3,
                )
                updated["supporting_evidence"] = (
                    result.supporting_evidence
                )
                updated["contradicting_evidence"] = (
                    result.contradicting_evidence
                )
                verified_claims.append(updated)

            else:
                try:
                    claim.status = result.status
                    claim.confidence_score = round(
                        result.score,
                        3,
                    )
                    claim.supporting_evidence = (
                        result.supporting_evidence
                    )
                    claim.contradicting_evidence = (
                        result.contradicting_evidence
                    )
                except Exception:
                    pass

                verified_claims.append(claim)

        return verified_claims


research_verifier = ResearchVerifier()
