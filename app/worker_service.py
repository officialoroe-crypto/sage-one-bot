"""Lifecycle-managed durable SAGE worker service.

The API persists work; this service is the local/cloud worker that actually
claims and executes queued root tasks. It is intentionally separate from
FastAPI request handling so a queued task cannot silently stall forever.
"""
from __future__ import annotations

import os
import threading
from datetime import datetime, timezone

from app.worker import SageWorker


def _enabled() -> bool:
    raw = os.getenv("SAGE_WORKER_ENABLED", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


class WorkerService:
    def __init__(self) -> None:
        self.worker = SageWorker()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self.started_at: str | None = None
        self.last_cycle_at: str | None = None
        self.last_result: dict | None = None
        self.last_error: str | None = None

    def start(self) -> None:
        if not _enabled():
            return
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self.started_at = datetime.now(timezone.utc).isoformat()
            self._thread = threading.Thread(
                target=self._run,
                name="sage-durable-worker",
                daemon=True,
            )
            self._thread.start()

    def _run(self) -> None:
        poll_seconds = max(
            0.25,
            float(os.getenv("SAGE_WORKER_POLL_SECONDS", "2.0")),
        )
        while not self._stop.is_set():
            try:
                result = self.worker.run_once()
                self.last_result = result
                self.last_cycle_at = datetime.now(timezone.utc).isoformat()
                self.last_error = None
                if result is None or result.get("status") == "deferred":
                    self._stop.wait(poll_seconds)
            except Exception as error:
                self.last_error = str(error)
                self.last_cycle_at = datetime.now(timezone.utc).isoformat()
                self._stop.wait(poll_seconds)

    def stop(self) -> None:
        with self._lock:
            self._stop.set()
            thread = self._thread
            self._thread = None
        if thread:
            thread.join(timeout=5)

    def health(self) -> dict:
        thread = self._thread
        return {
            "enabled": _enabled(),
            "running": bool(thread and thread.is_alive()),
            "worker_id": self.worker.worker_id,
            "started_at": self.started_at,
            "last_cycle_at": self.last_cycle_at,
            "last_result": self.last_result,
            "last_error": self.last_error,
        }


worker_service = WorkerService()
