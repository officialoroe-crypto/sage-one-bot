"""Task classification and CPU policy for local SAGE execution."""

from __future__ import annotations

from enum import Enum


class TaskClass(str, Enum):
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"


_HEAVY_KEYWORDS = (
    "research",
    "deep research",
    "synthesize",
    "synthesis",
    "verify sources",
    "cross-check",
    "crawl",
    "scrape",
    "analyze files",
    "large document",
    "long running",
    "video",
    "image generation",
    "embedding",
)

_MEDIUM_KEYWORDS = (
    "search",
    "web",
    "summarize",
    "extract",
    "compare",
    "plan",
    "analyze",
)


def classify_task(description: str) -> TaskClass:
    text = " ".join((description or "").lower().split())

    if any(keyword in text for keyword in _HEAVY_KEYWORDS):
        return TaskClass.HEAVY
    if any(keyword in text for keyword in _MEDIUM_KEYWORDS) or len(text) > 5000:
        return TaskClass.MEDIUM
    return TaskClass.LIGHT


def local_execution_allowed(task_class: TaskClass, cpu_percent: float) -> bool:
    """Return whether a task class should consume local CPU at this moment."""
    if cpu_percent >= 70:
        return False
    if task_class is TaskClass.HEAVY:
        return cpu_percent < 50
    if task_class is TaskClass.MEDIUM:
        return cpu_percent < 60
    return cpu_percent < 70
