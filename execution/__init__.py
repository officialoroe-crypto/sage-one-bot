"""Public execution package exports.

The execution package deliberately keeps imports lazy.  Several execution
modules are consumed by the brain router, while the execution engine itself
uses the brain router.  Eagerly importing the engine from this package during
package initialization creates a circular import.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "ConnectivityState",
    "ExecutionEngine",
    "ExecutionMode",
    "ExecutionModeRouter",
    "ExecutionScheduler",
    "MissionProgress",
    "ParallelMissionExecutor",
    "ResourceBand",
    "ResourceGuard",
    "ResourceSnapshot",
    "ScheduledTask",
    "TaskClass",
    "classify_task",
    "execution_engine",
    "local_execution_allowed",
    "mode_router",
    "parallel_mission_executor",
    "resource_guard",
    "scheduler",
]


_EXPORTS: dict[str, tuple[str, str]] = {
    "ExecutionEngine": ("execution.engine", "ExecutionEngine"),
    "execution_engine": ("execution.engine", "ExecutionEngine"),
    "ConnectivityState": ("execution.mode", "ConnectivityState"),
    "ExecutionMode": ("execution.mode", "ExecutionMode"),
    "ExecutionModeRouter": ("execution.mode", "ExecutionModeRouter"),
    "mode_router": ("execution.mode", "mode_router"),
    "TaskClass": ("execution.policy", "TaskClass"),
    "classify_task": ("execution.policy", "classify_task"),
    "local_execution_allowed": ("execution.policy", "local_execution_allowed"),
    "ResourceBand": ("execution.resource", "ResourceBand"),
    "ResourceGuard": ("execution.resource", "ResourceGuard"),
    "ResourceSnapshot": ("execution.resource", "ResourceSnapshot"),
    "resource_guard": ("execution.resource", "resource_guard"),
    "ExecutionScheduler": ("execution.scheduler", "ExecutionScheduler"),
    "ScheduledTask": ("execution.scheduler", "ScheduledTask"),
    "scheduler": ("execution.scheduler", "scheduler"),
    "MissionProgress": ("execution.progress", "MissionProgress"),
    "ParallelMissionExecutor": ("execution.parallel", "ParallelMissionExecutor"),
    "parallel_mission_executor": ("execution.parallel", "parallel_mission_executor"),
}

_execution_engine: Any | None = None


def __getattr__(name: str) -> Any:
    """Resolve public execution exports only when they are actually used."""
    global _execution_engine

    if name == "execution_engine":
        if _execution_engine is None:
            from execution.engine import ExecutionEngine

            _execution_engine = ExecutionEngine()
        return _execution_engine

    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = target
    module = __import__(module_name, fromlist=[attribute_name])
    value = getattr(module, attribute_name)

    globals()[name] = value
    return value
