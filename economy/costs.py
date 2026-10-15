"""SAGE Spark cost catalog for premium platform work.

Spark is the SAGE platform currency: 1 Spark = NPR 1 (see economy/currency.py).
These prices are quotes/catalog metadata and do not themselves charge a wallet.
"""

from __future__ import annotations

PREMIUM_WORK_COSTS = (
    {
        "key": "research_deep",
        "name": "Deep Research",
        "spark_cost": 25,
        "description": "Bounded multi-source research with verification and synthesis.",
    },
    {
        "key": "mission_heavy",
        "name": "Heavy Mission",
        "spark_cost": 50,
        "description": "A larger multi-step execution mission using background workers.",
    },
    {
        "key": "verification",
        "name": "Enhanced Verification",
        "spark_cost": 15,
        "description": "Additional cross-checking and evidence verification.",
    },
    {
        "key": "content_generation",
        "name": "Premium Content Work",
        "spark_cost": 20,
        "description": "Higher-effort content planning or generation work.",
    },
)


def cost_catalog() -> list[dict]:
    return [dict(item) for item in PREMIUM_WORK_COSTS]


def cost_for(work_key: str) -> int:
    for item in PREMIUM_WORK_COSTS:
        if item["key"] == work_key:
            return int(item["spark_cost"])
    raise KeyError(f"Unknown premium work type: {work_key}")
