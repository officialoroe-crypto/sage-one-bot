from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

from brain.router import router
from research.engine import research_engine
from research.verification import research_verifier


@dataclass
class ResearchClaim:
    claim_id: str
    claim: str
    classification: str
    source_ids: list[str]
    supporting_evidence: list[str]
    contradicting_evidence: list[str]
    confidence: str
    confidence_score: float
    status: str

    # Verification is deliberately separate from model confidence.
    verification_status: str = "UNVERIFIED"
    verification_score: float = 0.0
    verification_reason: str = ""


@dataclass
class ResearchReport:
    success: bool
    question: str
    summary: str
    key_findings: list[str]
    conflicts: list[str]
    uncertainties: list[str]
    analysis: list[str]
    sources: list[dict[str, Any]]
    source_count: int
    evidence_count: int
    claim_count: int
    created_at: str
    provider: str | None = None
    model: str | None = None
    error: str | None = None


class ResearchSynthesisEngine:

    # ---------------------------------------------------------
    # SYNTHESIS LIMITS
    # ---------------------------------------------------------

    MAX_CLAIMS = 12
    MAX_CONFLICTS = 10
    MAX_UNCERTAINTIES = 10
    MAX_ANALYSIS_ITEMS = 10

    MAX_EVIDENCE_PACK_CHARS = 24000
    MAX_CHARS_PER_EVIDENCE = 3500
    MAX_EVIDENCE_ITEMS = 16

    # ---------------------------------------------------------
    # TIME
    # ---------------------------------------------------------

    def _now(self) -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()

    # ---------------------------------------------------------
    # NORMALIZATION
    # ---------------------------------------------------------

    def _get_value(
        self,
        obj: Any,
        key: str,
        default: Any = None,
    ) -> Any:

        if isinstance(obj, dict):
            return obj.get(
                key,
                default,
            )

        return getattr(
            obj,
            key,
            default,
        )

    def _get_evidence(
        self,
        research_result: Any,
    ) -> list[dict[str, Any]]:

        evidence = self._get_value(
            research_result,
            "evidence",
            [],
        )

        if not isinstance(
            evidence,
            list,
        ):
            return []

        return [
            item
            for item in evidence
            if isinstance(
                item,
                dict,
            )
        ]

    def _get_sources(
        self,
        research_result: Any,
    ) -> list[Any]:

        sources = self._get_value(
            research_result,
            "sources",
            [],
        )

        if not isinstance(
            sources,
            list,
        ):
            return []

        return sources

    # ---------------------------------------------------------
    # JSON
    # ---------------------------------------------------------

    def _parse_json(
        self,
        response: str,
    ) -> dict[str, Any]:

        if not response:
            raise ValueError(
                "Empty synthesis response."
            )

        text = response.strip()

        try:
            parsed = json.loads(
                text
            )

        except json.JSONDecodeError:

            start = text.find("{")
            end = text.rfind("}")

            if start < 0 or end <= start:
                raise ValueError(
                    "Synthesis response does not "
                    "contain a JSON object."
                )

            parsed = json.loads(
                text[
                    start:end + 1
                ]
            )

        if not isinstance(
            parsed,
            dict,
        ):
            raise ValueError(
                "Synthesis response must be "
                "a JSON object."
            )

        return parsed

    # ---------------------------------------------------------
    # STRING HELPERS
    # ---------------------------------------------------------

    @staticmethod
    def _string_list(
        value: Any,
        limit: int,
    ) -> list[str]:

        if not isinstance(
            value,
            list,
        ):
            return []

        result: list[str] = []

        for item in value[:limit]:

            if isinstance(
                item,
                str,
            ):

                text = item.strip()

                if text:
                    result.append(
                        text
                    )

        return result

    @staticmethod
    def _clean_text(
        value: Any,
    ) -> str:

        if value is None:
            return ""

        text = str(value)

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    # ---------------------------------------------------------
    # TOKEN-LIKE ESTIMATION
    # ---------------------------------------------------------

    @staticmethod
    def _estimate_tokens(
        text: str,
    ) -> int:

        if not text:
            return 0

        return max(
            1,
            len(text) // 4,
        )

    # ---------------------------------------------------------
    # QUERY TERMS
    # ---------------------------------------------------------

    def _query_terms(
        self,
        question: str,
    ) -> set[str]:

        words = re.findall(
            r"[A-Za-z0-9][A-Za-z0-9_-]{2,}",
            question.lower(),
        )

        stop_words = {
            "what",
            "when",
            "where",
            "which",
            "who",
            "why",
            "how",
            "does",
            "did",
            "are",
            "the",
            "and",
            "for",
            "from",
            "with",
            "that",
            "this",
            "these",
            "those",
            "about",
            "into",
            "latest",
            "current",
            "2026",
        }

        return {
            word
            for word in words
            if word not in stop_words
        }

    # ---------------------------------------------------------
    # SENTENCE SPLITTING
    # ---------------------------------------------------------

    @staticmethod
    def _split_sentences(
        text: str,
    ) -> list[str]:

        if not text:
            return []

        normalized = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        if not normalized:
            return []

        sentences = re.split(
            r"(?<=[.!?])\s+",
            normalized,
        )

        return [
            sentence.strip()
            for sentence in sentences
            if sentence.strip()
        ]

    # ---------------------------------------------------------
    # SENTENCE SCORING
    # ---------------------------------------------------------

    def _score_sentence(
        self,
        sentence: str,
        query_terms: set[str],
    ) -> float:

        lower = sentence.lower()

        words = set(
            re.findall(
                r"[a-z0-9][a-z0-9_-]{2,}",
                lower,
            )
        )

        overlap = len(
            words.intersection(
                query_terms
            )
        )

        score = float(
            overlap * 4
        )

        factual_markers = (
            "according to",
            "reported",
            "announced",
            "found",
            "shows",
            "said",
            "confirmed",
            "research",
            "study",
            "data",
            "percent",
            "%",
            "million",
            "billion",
            "2026",
            "2025",
            "date",
            "launched",
            "released",
            "available",
            "developed",
            "introduced",
        )

        for marker in factual_markers:
            if marker in lower:
                score += 1.5

        length = len(sentence)

        if 80 <= length <= 500:
            score += 2

        elif length < 40:
            score -= 2

        boilerplate = (
            "cookie",
            "subscribe",
            "sign up",
            "newsletter",
            "privacy policy",
            "terms of service",
            "all rights reserved",
            "click here",
            "share this",
        )

        for marker in boilerplate:
            if marker in lower:
                score -= 8

        return score

    # ---------------------------------------------------------
    # EVIDENCE COMPRESSION
    # ---------------------------------------------------------

    def _compress_evidence_content(
        self,
        content: str,
        question: str,
        max_chars: int,
    ) -> str:

        content = self._clean_text(
            content
        )

        if not content:
            return ""

        if len(content) <= max_chars:
            return content

        sentences = self._split_sentences(
            content
        )

        if not sentences:
            return content[
                :max_chars
            ].strip()

        query_terms = self._query_terms(
            question
        )

        scored = []

        for index, sentence in enumerate(
            sentences
        ):

            score = self._score_sentence(
                sentence,
                query_terms,
            )

            scored.append(
                (
                    score,
                    index,
                    sentence,
                )
            )

        scored.sort(
            key=lambda item: (
                item[0],
                -item[1],
            ),
            reverse=True,
        )

        selected: list[tuple[int, str]] = []
        used_chars = 0

        if sentences:

            first = sentences[0]

            if len(first) <= max_chars:

                selected.append(
                    (
                        0,
                        first,
                    )
                )

                used_chars += (
                    len(first) + 1
                )

        for (
            score,
            index,
            sentence,
        ) in scored:

            if index == 0:
                continue

            sentence_length = len(
                sentence
            )

            if sentence_length > max_chars:
                continue

            if (
                used_chars
                + sentence_length
                + 1
                > max_chars
            ):
                continue

            selected.append(
                (
                    index,
                    sentence,
                )
            )

            used_chars += (
                sentence_length + 1
            )

            if used_chars >= max_chars:
                break

        selected.sort(
            key=lambda item: item[0]
        )

        result = " ".join(
            sentence
            for _, sentence
            in selected
        )

        return result[
            :max_chars
        ].strip()

    # ---------------------------------------------------------
    # EVIDENCE RELEVANCE
    # ---------------------------------------------------------

    def _score_evidence(
        self,
        item: dict[str, Any],
        question: str,
    ) -> float:

        query_terms = self._query_terms(
            question
        )

        title = self._clean_text(
            item.get("title")
        )

        content = self._clean_text(
            item.get("content")
        )

        source_id = self._clean_text(
            item.get("source_id")
        )

        combined = (
            title
            + " "
            + content[:6000]
        ).lower()

        words = set(
            re.findall(
                r"[a-z0-9][a-z0-9_-]{2,}",
                combined,
            )
        )

        overlap = len(
            words.intersection(
                query_terms
            )
        )

        score = float(
            overlap * 5
        )

        if title:
            score += 2

        if content:
            score += min(
                len(content) / 2000,
                4,
            )

        if source_id:
            score += 1

        return score

    # ---------------------------------------------------------
    # BUILD COMPRESSED EVIDENCE PACK
    # ---------------------------------------------------------

    def _build_evidence_pack(
        self,
        research_result: Any,
        question: str,
    ) -> tuple[str, dict[str, Any]]:

        evidence = self._get_evidence(
            research_result
        )

        if not evidence:
            return (
                "",
                {
                    "original_count": 0,
                    "included_count": 0,
                    "compressed_chars": 0,
                    "estimated_tokens": 0,
                },
            )

        ranked = []

        for index, item in enumerate(
            evidence
        ):

            evidence_id = item.get(
                "evidence_id"
            )

            if not evidence_id:
                continue

            score = self._score_evidence(
                item,
                question,
            )

            ranked.append(
                (
                    score,
                    index,
                    item,
                )
            )

        ranked.sort(
            key=lambda value: (
                value[0],
                -value[1],
            ),
            reverse=True,
        )

        selected = ranked[
            :self.MAX_EVIDENCE_ITEMS
        ]

        selected.sort(
            key=lambda value: value[1]
        )

        blocks: list[str] = []
        total_chars = 0

        for (
            score,
            index,
            item,
        ) in selected:

            evidence_id = self._clean_text(
                item.get(
                    "evidence_id"
                )
            )

            source_id = self._clean_text(
                item.get(
                    "source_id"
                )
            )

            title = self._clean_text(
                item.get(
                    "title"
                )
            )

            url = self._clean_text(
                item.get(
                    "url"
                )
            )

            content = self._compress_evidence_content(
                item.get(
                    "content",
                    ""
                ),
                question,
                self.MAX_CHARS_PER_EVIDENCE,
            )

            if not content:
                continue

            metadata = {
                "evidence_id": evidence_id,
                "source_id": source_id,
                "title": title,
                "url": url,
                "content": content,
            }

            block = json.dumps(
                metadata,
                ensure_ascii=False,
            )

            if (
                total_chars
                + len(block)
                + 1
                > self.MAX_EVIDENCE_PACK_CHARS
            ):
                break

            blocks.append(
                block
            )

            total_chars += (
                len(block) + 1
            )

        evidence_pack = "\n".join(
            blocks
        )

        stats = {
            "original_count": len(
                evidence
            ),
            "included_count": len(
                blocks
            ),
            "compressed_chars": len(
                evidence_pack
            ),
            "estimated_tokens": self._estimate_tokens(
                evidence_pack
            ),
        }

        return (
            evidence_pack,
            stats,
        )

    # ---------------------------------------------------------
    # SOURCES
    # ---------------------------------------------------------

    def _build_source_list(
        self,
        research_result: Any,
    ) -> list[dict[str, Any]]:

        sources = self._get_sources(
            research_result
        )

        result: list[dict[str, Any]] = []

        for source in sources:

            if hasattr(
                source,
                "__dataclass_fields__",
            ):

                data = asdict(
                    source
                )

            elif hasattr(
                source,
                "__dict__",
            ):

                data = dict(
                    source.__dict__
                )

            elif isinstance(
                source,
                dict,
            ):

                data = dict(
                    source
                )

            else:
                continue

            result.append(
                {
                    "source_id":
                        data.get(
                            "source_id"
                        ),

                    "title":
                        data.get(
                            "title"
                        ),

                    "url":
                        data.get(
                            "url"
                        ),

                    "site_name":
                        data.get(
                            "site_name"
                        ),

                    "author":
                        data.get(
                            "author"
                        ),

                    "publication_date":
                        data.get(
                            "publication_date"
                        ),
                }
            )

        return result

    # ---------------------------------------------------------
    # SCHEMA
    # ---------------------------------------------------------

    def _schema(
        self,
    ) -> dict[str, Any]:

        claim_schema = {
            "type": "object",

            "properties": {

                "claim_id": {
                    "type": "string",
                },

                "claim": {
                    "type": "string",
                },

                "classification": {
                    "type": "string",
                    "enum": [
                        "FACT",
                        "ANALYSIS",
                        "UNCERTAINTY",
                    ],
                },

                "source_ids": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },

                "supporting_evidence": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },

                "contradicting_evidence": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },

                "confidence": {
                    "type": "string",
                    "enum": [
                        "HIGH",
                        "MEDIUM",
                        "LOW",
                        "UNVERIFIED",
                    ],
                },

                "confidence_score": {
                    "type": "number",
                },

                "status": {
                    "type": "string",
                    "enum": [
                        "SUPPORTED",
                        "PARTIALLY_SUPPORTED",
                        "CONFLICTED",
                        "UNVERIFIED",
                    ],
                },
            },

            "required": [
                "claim_id",
                "claim",
                "classification",
                "source_ids",
                "supporting_evidence",
                "contradicting_evidence",
                "confidence",
                "confidence_score",
                "status",
            ],

            "additionalProperties": False,
        }

        return {
            "type": "object",

            "properties": {

                "summary": {
                    "type": "string",
                },

                "key_findings": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },

                "conflicts": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },

                "uncertainties": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },

                "analysis": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                },

                "claims": {
                    "type": "array",
                    "items": claim_schema,
                },
            },

            "required": [
                "summary",
                "key_findings",
                "conflicts",
                "uncertainties",
                "analysis",
                "claims",
            ],

            "additionalProperties": False,
        }

    # ---------------------------------------------------------
    # SYSTEM INSTRUCTION
    # ---------------------------------------------------------

    def _system_instruction(
        self,
    ) -> str:

        return """
You are the SAGE ONE research synthesis engine.

You receive compressed evidence extracted from real web sources.

Synthesize ONLY from the supplied evidence.

Rules:

1. Never invent sources.
2. Never invent URLs.
3. Never invent facts.
4. Every FACT claim must reference real source IDs.
5. Every claim should reference supporting evidence IDs when available.
6. Distinguish FACT, ANALYSIS, and UNCERTAINTY.
7. Explicitly identify conflicts when sources disagree.
8. Do not treat absence of evidence as proof.
9. Confidence must reflect the strength and directness of the supplied evidence.
10. If evidence is insufficient, say so.
11. Do not assume that a compressed passage contains information that was not supplied.
12. Produce useful findings.
13. Do not return an empty claims array when supplied evidence supports substantive findings.
14. supporting_evidence MUST contain evidence IDs, not source IDs.
15. contradicting_evidence MUST contain evidence IDs, not source IDs.
16. Do not claim that a fact is verified merely because your confidence is HIGH.
17. Return only the requested JSON object.
"""

    # ---------------------------------------------------------
    # CLAIM VALIDATION
    # ---------------------------------------------------------

    def _validate_claim(
        self,
        claim: dict[str, Any],
        valid_source_ids: set[str],
        valid_evidence_ids: set[str],
    ) -> ResearchClaim:

        source_ids = [
            source_id
            for source_id in self._string_list(
                claim.get(
                    "source_ids"
                ),
                20,
            )
            if source_id in valid_source_ids
        ]

        supporting = [
            evidence_id
            for evidence_id in self._string_list(
                claim.get(
                    "supporting_evidence"
                ),
                20,
            )
            if evidence_id in valid_evidence_ids
        ]

        contradicting = [
            evidence_id
            for evidence_id in self._string_list(
                claim.get(
                    "contradicting_evidence"
                ),
                20,
            )
            if evidence_id in valid_evidence_ids
        ]

        classification = str(
            claim.get(
                "classification",
                "UNCERTAINTY",
            )
        ).upper()

        if classification not in {
            "FACT",
            "ANALYSIS",
            "UNCERTAINTY",
        }:
            classification = "UNCERTAINTY"

        confidence = str(
            claim.get(
                "confidence",
                "LOW",
            )
        ).upper()

        if confidence not in {
            "HIGH",
            "MEDIUM",
            "LOW",
            "UNVERIFIED",
        }:
            confidence = "LOW"

        status = str(
            claim.get(
                "status",
                "UNVERIFIED",
            )
        ).upper()

        if status not in {
            "SUPPORTED",
            "PARTIALLY_SUPPORTED",
            "CONFLICTED",
            "UNVERIFIED",
        }:
            status = "UNVERIFIED"

        try:

            confidence_score = float(
                claim.get(
                    "confidence_score",
                    0.0,
                )
            )

        except Exception:

            confidence_score = 0.0

        confidence_score = max(
            0.0,
            min(
                1.0,
                confidence_score,
            ),
        )

        if (
            classification == "FACT"
            and not source_ids
        ):

            confidence = "UNVERIFIED"
            status = "UNVERIFIED"
            confidence_score = 0.0

        if (
            status == "SUPPORTED"
            and not source_ids
        ):

            status = "UNVERIFIED"
            confidence = "UNVERIFIED"
            confidence_score = 0.0

        return ResearchClaim(
            claim_id=str(
                claim.get(
                    "claim_id",
                    "",
                )
            ),

            claim=str(
                claim.get(
                    "claim",
                    "",
                )
            ).strip(),

            classification=classification,

            source_ids=source_ids,

            supporting_evidence=supporting,

            contradicting_evidence=contradicting,

            confidence=confidence,

            confidence_score=confidence_score,

            status=status,
        )

    # ---------------------------------------------------------
    # VERIFICATION
    # ---------------------------------------------------------

    def _verify_claims(
        self,
        claims: list[ResearchClaim],
        evidence: list[dict[str, Any]],
    ) -> list[ResearchClaim]:

        for claim in claims:

            verification = (
                research_verifier.verify_claim(
                    claim,
                    evidence,
                )
            )

            claim.verification_status = (
                verification.status
            )

            claim.verification_score = round(
                verification.score,
                3,
            )

            claim.verification_reason = (
                verification.reason
            )

            # The verifier is authoritative for
            # verification status, but NOT for the
            # model's original confidence.
            #
            # Keep the model's supporting evidence
            # when it is valid, but replace it with
            # deterministic verifier evidence when
            # the verifier has stronger traceability.
            if verification.supporting_evidence:

                claim.supporting_evidence = list(
                    dict.fromkeys(
                        verification.supporting_evidence
                    )
                )

            if verification.contradicting_evidence:

                claim.contradicting_evidence = list(
                    dict.fromkeys(
                        verification.contradicting_evidence
                    )
                )

        return claims

    # ---------------------------------------------------------
    # SYNTHESIS
    # ---------------------------------------------------------

    def synthesize(
        self,
        question: str,
        max_queries: int = 5,
        max_results_per_query: int = 5,
        research_result=None,
    ) -> dict[str, Any]:

        try:

            if research_result is None:

                research_result = (
                    research_engine.research(
                        question=question,
                        max_queries=max_queries,
                        max_results_per_query=(
                            max_results_per_query
                        ),
                    )
                )

            # -------------------------------------------------
            # NORMALIZE RESEARCH RESULT
            # -------------------------------------------------

            evidence = self._get_evidence(
                research_result
            )

            sources = self._get_sources(
                research_result
            )

            if not evidence:

                return {
                    "success": False,
                    "question": question,
                    "error":
                        "Research produced no usable evidence.",
                    "source_count":
                        len(sources),
                    "evidence_count":
                        0,
                }

            # -------------------------------------------------
            # COMPRESS EVIDENCE
            # -------------------------------------------------

            (
                evidence_pack,
                compression_stats,
            ) = self._build_evidence_pack(
                research_result,
                question,
            )

            if not evidence_pack.strip():

                return {
                    "success": False,
                    "question": question,
                    "error":
                        "Research evidence pack is empty.",
                    "source_count":
                        len(sources),
                    "evidence_count":
                        len(evidence),
                }

            source_list = (
                self._build_source_list(
                    research_result
                )
            )

            valid_source_ids = {
                str(
                    source.get(
                        "source_id"
                    )
                )
                for source in source_list
                if source.get(
                    "source_id"
                )
            }

            valid_evidence_ids = {
                str(
                    item.get(
                        "evidence_id"
                    )
                )
                for item in evidence
                if item.get(
                    "evidence_id"
                )
            }

            # -------------------------------------------------
            # SYNTHESIS INPUT
            # -------------------------------------------------

            user_message = (
                "Research question:\n"
                + question
                + "\n\n"
                + "Compressed evidence:\n"
                + evidence_pack
            )

            provider_result = (
                router.think_structured(
                    system_instruction=(
                        self._system_instruction()
                    ),

                    user_message=(
                        user_message
                    ),

                    schema=(
                        self._schema()
                    ),

                    schema_name=(
                        "sage_research_report"
                    ),
                )
            )

            parsed = self._parse_json(
                provider_result.response
            )

            # -------------------------------------------------
            # CLAIMS
            # -------------------------------------------------

            raw_claims = parsed.get(
                "claims",
                [],
            )

            if not isinstance(
                raw_claims,
                list,
            ):
                raw_claims = []

            claims: list[
                ResearchClaim
            ] = []

            for raw_claim in raw_claims[
                :self.MAX_CLAIMS
            ]:

                if not isinstance(
                    raw_claim,
                    dict,
                ):
                    continue

                claim = self._validate_claim(
                    raw_claim,
                    valid_source_ids,
                    valid_evidence_ids,
                )

                if claim.claim:
                    claims.append(
                        claim
                    )

            # -------------------------------------------------
            # REPORT FIELDS
            # -------------------------------------------------

            summary = str(
                parsed.get(
                    "summary",
                    "",
                )
            ).strip()

            key_findings = (
                self._string_list(
                    parsed.get(
                        "key_findings"
                    ),
                    self.MAX_CLAIMS,
                )
            )

            conflicts = (
                self._string_list(
                    parsed.get(
                        "conflicts"
                    ),
                    self.MAX_CONFLICTS,
                )
            )

            uncertainties = (
                self._string_list(
                    parsed.get(
                        "uncertainties"
                    ),
                    self.MAX_UNCERTAINTIES,
                )
            )

            analysis = (
                self._string_list(
                    parsed.get(
                        "analysis"
                    ),
                    self.MAX_ANALYSIS_ITEMS,
                )
            )

            # -------------------------------------------------
            # SUBSTANTIVE SUCCESS CHECK
            # -------------------------------------------------

            if not summary:

                raise RuntimeError(
                    "Synthesis provider returned "
                    "an empty summary."
                )

            if not claims:

                raise RuntimeError(
                    "Synthesis provider returned "
                    "zero usable claims."
                )

            # -------------------------------------------------
            # VERIFY EVERY CLAIM
            # -------------------------------------------------

            claims = self._verify_claims(
                claims,
                evidence,
            )

            # -------------------------------------------------
            # VERIFICATION STATISTICS
            # -------------------------------------------------

            verification_counts = {
                "VERIFIED": 0,
                "PARTIALLY_VERIFIED": 0,
                "CONTRADICTED": 0,
                "UNVERIFIED": 0,
            }

            verification_scores: list[float] = []

            for claim in claims:

                status = (
                    claim.verification_status
                )

                if status in verification_counts:

                    verification_counts[
                        status
                    ] += 1

                verification_scores.append(
                    claim.verification_score
                )

            average_verification_score = 0.0

            if verification_scores:

                average_verification_score = round(
                    sum(
                        verification_scores
                    )
                    / len(
                        verification_scores
                    ),
                    3,
                )

            # -------------------------------------------------
            # REPORT
            # -------------------------------------------------

            report = ResearchReport(
                success=True,

                question=question,

                summary=summary,

                key_findings=key_findings,

                conflicts=conflicts,

                uncertainties=uncertainties,

                analysis=analysis,

                sources=source_list,

                source_count=len(
                    sources
                ),

                evidence_count=len(
                    evidence
                ),

                claim_count=len(
                    claims
                ),

                created_at=self._now(),

                provider=(
                    provider_result.provider
                ),

                model=(
                    provider_result.model
                ),
            )

            return {
                **asdict(
                    report
                ),

                "claims": [
                    asdict(
                        claim
                    )
                    for claim in claims
                ],

                "pipeline": {

                    "search": {
                        "completed": True,
                        "source_count":
                            len(
                                sources
                            ),
                    },

                    "read": {
                        "completed": True,
                    },

                    "evidence": {
                        "completed": True,
                        "count":
                            len(
                                evidence
                            ),
                        "compression": {
                            "original_count":
                                compression_stats[
                                    "original_count"
                                ],

                            "included_count":
                                compression_stats[
                                    "included_count"
                                ],

                            "compressed_chars":
                                compression_stats[
                                    "compressed_chars"
                                ],

                            "estimated_tokens":
                                compression_stats[
                                    "estimated_tokens"
                                ],
                        },
                    },

                    "claims": {
                        "completed": True,
                        "count":
                            len(
                                claims
                            ),
                    },

                    "synthesis": {
                        "completed": True,
                        "status":
                            "completed",
                    },

                    "verification": {
                        "completed": True,
                        "status": "completed",

                        "claim_count":
                            len(
                                claims
                            ),

                        "verified":
                            verification_counts[
                                "VERIFIED"
                            ],

                        "partially_verified":
                            verification_counts[
                                "PARTIALLY_VERIFIED"
                            ],

                        "contradicted":
                            verification_counts[
                                "CONTRADICTED"
                            ],

                        "unverified":
                            verification_counts[
                                "UNVERIFIED"
                            ],

                        "average_score":
                            average_verification_score,
                    },
                },
            }

        except Exception as error:

            return {
                "success": False,

                "question": question,

                "summary": "",

                "key_findings": [],

                "conflicts": [],

                "uncertainties": [],

                "analysis": [],

                "claims": [],

                "sources": [],

                "source_count": 0,

                "evidence_count": 0,

                "claim_count": 0,

                "created_at": self._now(),

                "provider": None,

                "model": None,

                "error": str(
                    error
                ),

                "pipeline": {
                    "synthesis": {
                        "completed": False,
                        "status": "failed",
                    },
                },
            }


research_synthesis_engine = (
    ResearchSynthesisEngine()
)