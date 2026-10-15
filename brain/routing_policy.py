"""Deterministic provider-routing policy for SAGE ONE.

Routing is deliberately conservative: cloud providers handle medium/heavy
work, while Ollama is only eligible for light work when the local host has
room. No provider is selected here by secret availability alone; the caller
still checks provider availability and cooldown state.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from execution.policy import TaskClass, classify_task
from execution.resource import ResourceSnapshot


class RoutingMode(str, Enum):
    AUTO = "auto"
    CLOUD = "cloud"
    LOCAL = "local"


@dataclass(frozen=True)
class RoutingDecision:
    task_class: TaskClass
    mode: RoutingMode
    provider_order: tuple[str, ...]
    local_allowed: bool
    reason: str


def decide_routing(
    description: str,
    snapshot: ResourceSnapshot | None = None,
    mode: str = "auto",
    prefer_local: bool = False,
) -> RoutingDecision:
    """Choose an ordered provider strategy without performing any inference."""
    try:
        routing_mode = RoutingMode(mode.lower())
    except ValueError as exc:
        raise ValueError(
            f"Invalid routing mode: {mode!r}. "
            f"Expected one of {[item.value for item in RoutingMode]}."
        ) from exc

    task_class = classify_task(description)
    cpu = snapshot.cpu_percent if snapshot is not None else None
    local_allowed = (
        snapshot is not None
        and snapshot.cpu_percent < 70.0
        and task_class is TaskClass.LIGHT
    )

    if routing_mode is RoutingMode.LOCAL:
        if task_class is not TaskClass.LIGHT:
            return RoutingDecision(
                task_class=task_class,
                mode=routing_mode,
                provider_order=(),
                local_allowed=False,
                reason="Local-only mode refuses medium/heavy work.",
            )
        if snapshot is None:
            return RoutingDecision(
                task_class=task_class,
                mode=routing_mode,
                provider_order=(),
                local_allowed=False,
                reason="Local-only mode requires a resource snapshot.",
            )
        if not local_allowed:
            return RoutingDecision(
                task_class=task_class,
                mode=routing_mode,
                provider_order=(),
                local_allowed=False,
                reason=f"Local CPU protection blocked work at {cpu:.1f}% CPU.",
            )
        return RoutingDecision(
            task_class=task_class,
            mode=routing_mode,
            provider_order=("ollama",),
            local_allowed=True,
            reason="Explicit local mode for a light task.",
        )

    if routing_mode is RoutingMode.CLOUD:
        return RoutingDecision(
            task_class=task_class,
            mode=routing_mode,
            provider_order=("groq", "cerebras", "gemini"),
            local_allowed=False,
            reason="Explicit cloud mode; local inference is disabled.",
        )

    if task_class in {TaskClass.MEDIUM, TaskClass.HEAVY}:
        return RoutingDecision(
            task_class=task_class,
            mode=routing_mode,
            provider_order=("groq", "cerebras", "gemini"),
            local_allowed=False,
            reason="Medium/heavy work is cloud-first and never falls back to local Ollama.",
        )

    if prefer_local and local_allowed:
        return RoutingDecision(
            task_class=task_class,
            mode=routing_mode,
            provider_order=("ollama", "groq", "cerebras", "gemini"),
            local_allowed=True,
            reason="Local preference enabled and host CPU is below the local ceiling.",
        )

    if local_allowed:
        return RoutingDecision(
            task_class=task_class,
            mode=routing_mode,
            provider_order=("groq", "cerebras", "gemini", "ollama"),
            local_allowed=True,
            reason="Cloud-first light work with safe local fallback available.",
        )

    return RoutingDecision(
        task_class=task_class,
        mode=routing_mode,
        provider_order=("groq", "cerebras", "gemini"),
        local_allowed=False,
        reason="Local resource state is unknown or above the safe ceiling; use cloud only.",
    )
