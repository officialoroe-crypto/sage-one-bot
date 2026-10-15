"""User-facing and durable mission progress events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from missions.history import append_event


class MissionProgress:
    """Collect deterministic progress events for one mission execution.

    Events are retained in memory for the current execution and persisted to
    the durable mission history store as they are emitted. Persistence is
    intentionally best-effort: a history-store failure must not break the
    underlying mission execution path.
    """

    def __init__(self, mission_id: str, *, persist: bool = True):
        self.mission_id = mission_id
        self.persist = persist
        self._events: list[dict[str, Any]] = []

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def emit(
        self,
        event_type: str,
        status: str,
        message: str,
        *,
        wave: int = 0,
        task_ids: list[str] | None = None,
        progress_percent: float = 0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event: dict[str, Any] = {
            "sequence": len(self._events) + 1,
            "mission_id": self.mission_id,
            "event_type": event_type,
            "status": status,
            "message": message,
            "wave": wave,
            "task_ids": sorted(task_ids or []),
            "progress_percent": round(float(progress_percent), 2),
            "metadata": metadata or {},
            "created_at": self._now(),
        }
        self._events.append(event)

        if self.persist:
            try:
                persisted = append_event(
                    mission_id=self.mission_id,
                    event=event,
                )
                event["id"] = persisted["id"]
                event["sequence"] = persisted["sequence"]
            except Exception:
                # Execution must remain independent from observability/history.
                # The in-memory event is still available to the caller.
                pass

        return event

    def snapshot(self) -> list[dict[str, Any]]:
        return list(self._events)
