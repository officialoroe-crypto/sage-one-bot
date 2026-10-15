"""Provider error classification and durable resilience telemetry."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from database.connection import engine


CREATE_TELEMETRY_TABLE = """
CREATE TABLE IF NOT EXISTS provider_telemetry (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    model TEXT,
    operation TEXT NOT NULL,
    outcome TEXT NOT NULL,
    error_class TEXT,
    duration_ms REAL NOT NULL,
    fallback_index INTEGER NOT NULL DEFAULT 0,
    structured INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    created_at TEXT NOT NULL
)
"""

CREATE_TELEMETRY_INDEX = """
CREATE INDEX IF NOT EXISTS ix_provider_telemetry_provider_created
ON provider_telemetry (provider, created_at)
"""


ERROR_CLASSES = {
    "quota": "quota",
    "auth": "authentication",
    "invalid_request": "invalid_request",
    "not_found": "not_found",
    "transient": "transient",
    "output": "output",
    "unknown": "unknown",
}

COOLDOWN_SECONDS = {
    "quota": 120.0,
    "authentication": 300.0,
    "invalid_request": 300.0,
    "not_found": 300.0,
    "transient": 30.0,
    "output": 15.0,
    "unknown": 30.0,
}


def ensure_telemetry_store() -> None:
    with engine.begin() as connection:
        connection.execute(text(CREATE_TELEMETRY_TABLE))
        connection.execute(text(CREATE_TELEMETRY_INDEX))


def classify_error(error: Exception | str) -> str:
    """Classify provider failures without inspecting or storing prompts."""
    message = str(error).lower()

    if any(
        marker in message
        for marker in (
            "429",
            "rate limit",
            "rate_limit",
            "quota",
            "too many requests",
            "resource exhausted",
        )
    ):
        return "quota"

    if any(
        marker in message
        for marker in (
            "401",
            "403",
            "unauthorized",
            "forbidden",
            "authentication",
            "api key",
            "invalid api key",
        )
    ):
        return "authentication"

    if any(
        marker in message
        for marker in (
            "404",
            "not found",
            "model does not exist",
            "unknown model",
        )
    ):
        return "not_found"

    if any(
        marker in message
        for marker in (
            "400",
            "invalid request",
            "bad request",
            "unsupported parameter",
            "invalid argument",
        )
    ):
        return "invalid_request"

    if any(
        marker in message
        for marker in (
            "empty response",
            "empty content",
            "invalid json",
            "structured output",
            "maximum of",
        )
    ):
        return "output"

    if any(
        marker in message
        for marker in (
            "timeout",
            "timed out",
            "connection",
            "temporarily unavailable",
            "503",
            "502",
            "504",
            "service unavailable",
        )
    ):
        return "transient"

    return "unknown"


def cooldown_for(error_class: str) -> float:
    return COOLDOWN_SECONDS.get(error_class, COOLDOWN_SECONDS["unknown"])


def record_telemetry(
    *,
    provider: str,
    model: str | None,
    operation: str,
    outcome: str,
    duration_ms: float,
    fallback_index: int = 0,
    structured: bool = False,
    error_class: str | None = None,
    error: Exception | str | None = None,
) -> None:
    """Best-effort durable provider telemetry; never affects inference."""
    try:
        ensure_telemetry_store()
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO provider_telemetry
                    (id, provider, model, operation, outcome, error_class,
                     duration_ms, fallback_index, structured, error, created_at)
                    VALUES
                    (:id, :provider, :model, :operation, :outcome, :error_class,
                     :duration_ms, :fallback_index, :structured, :error, :created_at)
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "provider": provider,
                    "model": model,
                    "operation": operation,
                    "outcome": outcome,
                    "error_class": error_class,
                    "duration_ms": round(float(duration_ms), 2),
                    "fallback_index": int(fallback_index),
                    "structured": 1 if structured else 0,
                    "error": str(error)[:1000] if error is not None else None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )
    except Exception:
        pass


def telemetry_summary(limit: int = 100) -> dict[str, Any]:
    """Return compact provider telemetry without exposing request contents."""
    ensure_telemetry_store()
    limit = max(1, min(int(limit), 1000))

    with engine.begin() as connection:
        rows = connection.execute(
            text(
                """
                SELECT provider, operation, outcome, error_class,
                       duration_ms, fallback_index, structured, created_at
                FROM provider_telemetry
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"limit": limit},
        ).mappings().all()

    return {
        "count": len(rows),
        "events": [dict(row) for row in rows],
    }
