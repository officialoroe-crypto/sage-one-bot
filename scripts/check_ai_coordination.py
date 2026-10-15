#!/usr/bin/env python3
"""Validate SAGE ONE AI work coordination state."""
from pathlib import Path
import importlib.util
import sys

state = Path("coordination/ACTIVE_WORK.yaml")
if not state.exists():
    raise SystemExit("coordination/ACTIVE_WORK.yaml is missing")

spec = importlib.util.spec_from_file_location(
    "sage_coordination_claims",
    Path("coordination/claims.py"),
)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

claims = module.parse_claims(state.read_text(encoding="utf-8"))

required = (
    "id", "agent", "branch", "base_sha", "objective",
    "status", "started_at", "updated_at",
)

seen = set()
for claim in claims:
    missing = [key for key in required if not claim.get(key)]
    if missing:
        raise SystemExit(
            f"Claim {claim.get('id', '<unknown>')} missing: "
            + ", ".join(missing)
        )
    if claim["id"] in seen:
        raise SystemExit(f"Duplicate active claim id: {claim['id']}")
    seen.add(claim["id"])
    if claim["status"] not in {
        "claimed", "in_progress", "blocked", "handoff", "ready_for_review"
    }:
        raise SystemExit(
            f"Invalid active claim status for {claim['id']}: {claim['status']}"
        )
    if module.stale(claim):
        raise SystemExit(
            f"Stale active claim requires explicit takeover/handoff: {claim['id']}"
        )

for index, left in enumerate(claims):
    for right in claims[index + 1:]:
        for left_path in left.get("scope", []):
            for right_path in right.get("scope", []):
                if module.overlaps(left_path, right_path):
                    raise SystemExit(
                        f"Overlapping active claims: {left['id']} and {right['id']}"
                    )

print(
    "AI coordination check: PASS "
    f"({len(claims)} active claim(s), no stale/overlapping claims)"
)
