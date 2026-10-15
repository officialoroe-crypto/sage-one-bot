"""First-run onboarding contract for SAGE ONE."""

from __future__ import annotations

from typing import Any


ONBOARDING_VERSION = 1

# Short labels are intentionally stable: the same capability IDs can power
# Flutter chips now and future web/desktop onboarding later.
CAPABILITIES: tuple[dict[str, Any], ...] = (
    {"id": "personal_mentor", "label": "Personal mentor"},
    {"id": "learning", "label": "Learn & improve skills"},
    {"id": "research", "label": "Research & find information"},
    {"id": "work", "label": "Find work & opportunities"},
    {"id": "business", "label": "Business, marketing & sales"},
    {"id": "content", "label": "Content, video & creative work"},
    {"id": "planning", "label": "Plan goals & execute tasks"},
    {"id": "productivity", "label": "Organize life & productivity"},
)

CAPABILITY_IDS = {item["id"] for item in CAPABILITIES}


def capability_catalog() -> dict[str, Any]:
    return {
        "version": ONBOARDING_VERSION,
        "capabilities": [dict(item) for item in CAPABILITIES],
        "multi_select": True,
    }


def validate_capabilities(values: list[str]) -> list[str]:
    cleaned = sorted({value.strip() for value in values if value and value.strip()})
    unknown = [value for value in cleaned if value not in CAPABILITY_IDS]
    if unknown:
        raise ValueError(f"Unknown onboarding capabilities: {unknown}")
    return cleaned
