"""Consent-gated profile memory learning pipeline.

This layer accepts already-classified memory candidates from a trusted
conversation/agent layer. It never stores raw conversation transcripts.
Automatic learning is allowed only when the owner's persisted memory consent
is enabled.
"""

from __future__ import annotations

import re
from typing import Any

from identity.memory import MEMORY_TYPES, add_memory, list_memory


_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(?:password|passwd|api[_ -]?key|secret|access[_ -]?token)\s*[:=]\s*\S+"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
)


def _normalize(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _looks_like_secret(value: str) -> bool:
    return any(pattern.search(value) for pattern in _SECRET_PATTERNS)


def learn_memory_candidates(
    *,
    profile_id: str,
    memory_consent: bool,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Persist safe, classified candidates only when consent is active.

    Candidates are deliberately stored as unconfirmed. Consent authorizes
    automatic persistence; it does not turn an inference into a confirmed fact.
    """
    if not memory_consent:
        return {
            "success": False,
            "status": "consent_required",
            "learned": [],
            "skipped": [],
            "rejected": [{"reason": "memory_consent_disabled"}],
        }

    existing = {_normalize(item["content"]) for item in list_memory(profile_id, limit=1000)}
    learned: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for candidate in candidates:
        memory_type = str(candidate.get("memory_type", "")).strip()
        content = str(candidate.get("content", "")).strip()
        importance = float(candidate.get("importance", 0.5))
        confidence = float(candidate.get("confidence", 0.75))

        if memory_type not in MEMORY_TYPES:
            rejected.append({"content": content, "reason": "unsupported_memory_type"})
            continue
        if not content:
            rejected.append({"reason": "empty_content"})
            continue
        if len(content) > 5000:
            rejected.append({"reason": "content_too_long"})
            continue
        if not 0.0 <= importance <= 1.0:
            rejected.append({"content": content, "reason": "invalid_importance"})
            continue
        if not 0.0 <= confidence <= 1.0:
            rejected.append({"content": content, "reason": "invalid_confidence"})
            continue
        if _looks_like_secret(content):
            rejected.append({"reason": "secret_like_content"})
            continue

        key = _normalize(content)
        if key in existing:
            skipped.append({"content": content, "reason": "duplicate"})
            continue

        memory = add_memory(
            profile_id=profile_id,
            memory_type=memory_type,
            content=content,
            importance=importance,
            confidence=confidence,
            source="auto_learning",
            confirmed=False,
        )
        existing.add(key)
        learned.append(memory)

    return {
        "success": True,
        "status": "learned",
        "learned": learned,
        "skipped": skipped,
        "rejected": rejected,
    }
