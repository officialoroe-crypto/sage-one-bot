"""Durable mission execution event history.

The mission progress collector remains lightweight, while this module provides
an append-only SQLite-compatible event store for long-term mission history.
The table is created lazily so existing deployments do not require a migration
runner for this additive checkpoint.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from database.connection import engine


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS mission_execution_events (
    id TEXT PRIMARY KEY,
    mission_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    wave INTEGER NOT NULL DEFAULT 0,
    task_ids TEXT,
    progress_percent REAL NOT NULL DEFAULT 0,
    metadata TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(mission_id, sequence)
)
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS ix_mission_execution_events_mission
ON mission_execution_events (mission_id, sequence)
"""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_event_store() -> None:
    with engine.begin() as connection:
        connection.execute(text(_CREATE_TABLE))
        connection.execute(text(_CREATE_INDEX))


def append_event(
    *,
    mission_id: str,
    event: dict[str, Any],
) -> dict[str, Any]:
    """Persist one normalized event using the next durable mission sequence."""

    ensure_event_store()

    event_id = str(uuid.uuid4())
    created_at = str(event.get("created_at") or _now().isoformat())

    with engine.begin() as connection:
        next_sequence = connection.execute(
            text(
                """
                SELECT COALESCE(MAX(sequence), 0) + 1
                FROM mission_execution_events
                WHERE mission_id = :mission_id
                """
            ),
            {"mission_id": mission_id},
        ).scalar_one()
        sequence = int(next_sequence)

        connection.execute(
            text(
                """
                INSERT INTO mission_execution_events
                (id, mission_id, sequence, event_type, status, message,
                 wave, task_ids, progress_percent, metadata, created_at)
                VALUES
                (:id, :mission_id, :sequence, :event_type, :status, :message,
                 :wave, :task_ids, :progress_percent, :metadata, :created_at)
                """
            ),
            {
                "id": event_id,
                "mission_id": mission_id,
                "sequence": sequence,
                "event_type": str(event.get("event_type", "unknown")),
                "status": str(event.get("status", "unknown")),
                "message": str(event.get("message", "")),
                "wave": int(event.get("wave", 0) or 0),
                "task_ids": json.dumps(
                    sorted(event.get("task_ids") or []),
                    ensure_ascii=False,
                ),
                "progress_percent": round(
                    float(event.get("progress_percent", 0) or 0),
                    2,
                ),
                "metadata": json.dumps(
                    event.get("metadata") or {},
                    ensure_ascii=False,
                    default=str,
                ),
                "created_at": created_at,
            },
        )

    payload = dict(event)
    payload["mission_id"] = mission_id
    payload["created_at"] = created_at
    payload["sequence"] = sequence
    payload["id"] = event_id
    return payload


def list_events(
    mission_id: str,
    *,
    limit: int = 200,
) -> list[dict[str, Any]]:
    """Return mission events in deterministic durable execution order."""

    ensure_event_store()
    limit = max(1, min(int(limit), 1000))

    with engine.begin() as connection:
        rows = connection.execute(
            text(
                """
                SELECT id, mission_id, sequence, event_type, status, message,
                       wave, task_ids, progress_percent, metadata, created_at
                FROM mission_execution_events
                WHERE mission_id = :mission_id
                ORDER BY sequence ASC
                LIMIT :limit
                """
            ),
            {"mission_id": mission_id, "limit": limit},
        ).mappings().all()

    events: list[dict[str, Any]] = []
    for row in rows:
        try:
            task_ids = json.loads(row["task_ids"] or "[]")
        except Exception:
            task_ids = []
        try:
            metadata = json.loads(row["metadata"] or "{}")
        except Exception:
            metadata = {}

        events.append(
            {
                "id": row["id"],
                "mission_id": row["mission_id"],
                "sequence": int(row["sequence"]),
                "event_type": row["event_type"],
                "status": row["status"],
                "message": row["message"],
                "wave": int(row["wave"]),
                "task_ids": task_ids,
                "progress_percent": round(float(row["progress_percent"]), 2),
                "metadata": metadata,
                "created_at": row["created_at"],
            }
        )

    return events


def latest_event(mission_id: str) -> dict[str, Any] | None:
    """Return the highest-sequence event for a mission."""
    ensure_event_store()

    with engine.begin() as connection:
        row = connection.execute(
            text(
                """
                SELECT id, mission_id, sequence, event_type, status, message,
                       wave, task_ids, progress_percent, metadata, created_at
                FROM mission_execution_events
                WHERE mission_id = :mission_id
                ORDER BY sequence DESC
                LIMIT 1
                """
            ),
            {"mission_id": mission_id},
        ).mappings().first()

    if row is None:
        return None

    try:
        task_ids = json.loads(row["task_ids"] or "[]")
    except Exception:
        task_ids = []
    try:
        metadata = json.loads(row["metadata"] or "{}")
    except Exception:
        metadata = {}

    return {
        "id": row["id"],
        "mission_id": row["mission_id"],
        "sequence": int(row["sequence"]),
        "event_type": row["event_type"],
        "status": row["status"],
        "message": row["message"],
        "wave": int(row["wave"]),
        "task_ids": task_ids,
        "progress_percent": round(float(row["progress_percent"]), 2),
        "metadata": metadata,
        "created_at": row["created_at"],
    }
