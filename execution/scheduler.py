from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock
from uuid import uuid4
from typing import Any, Callable

from execution.resource import ResourceGuard, resource_guard


@dataclass(frozen=True)
class ScheduledTask:
    task_id: str
    priority: int = 0


class ExecutionScheduler:
    """Bounded local scheduler with resource protection.

    This scheduler is intentionally non-persistent. Durable task state belongs
    to the task engine; this layer only controls in-process concurrency.
    """

    def __init__(
        self,
        max_workers: int = 2,
        guard: ResourceGuard | None = None,
    ) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be at least 1")
        self.max_workers = max_workers
        self.guard = guard or resource_guard
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = Lock()
        self._futures: dict[str, Future[Any]] = {}

    def submit(
        self,
        fn: Callable[..., Any],
        *args: Any,
        task_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        snapshot = self.guard.snapshot()
        if self.guard.should_block(snapshot):
            raise RuntimeError(
                f"Local CPU protection active at {snapshot.cpu_percent:.1f}%"
            )

        identifier = task_id or str(uuid4())
        future = self._executor.submit(fn, *args, **kwargs)
        with self._lock:
            self._futures[identifier] = future
        return identifier

    def status(self, task_id: str) -> dict[str, Any]:
        with self._lock:
            future = self._futures.get(task_id)

        if future is None:
            return {"success": False, "error": "Task not found."}
        if future.cancelled():
            state = "cancelled"
        elif future.running():
            state = "running"
        elif future.done():
            state = "completed" if future.exception() is None else "failed"
        else:
            state = "pending"

        result = None
        error = None
        if future.done() and not future.cancelled():
            try:
                result = future.result()
            except Exception as exc:  # pragma: no cover - defensive path
                error = str(exc)

        return {
            "success": True,
            "task_id": task_id,
            "status": state,
            "result": result,
            "error": error,
        }

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            future = self._futures.get(task_id)
        return bool(future and future.cancel())

    def shutdown(self, wait: bool = True) -> None:
        self._executor.shutdown(wait=wait, cancel_futures=True)


scheduler = ExecutionScheduler()
