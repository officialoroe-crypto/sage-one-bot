#!/usr/bin/env python3
"""Local, fail-closed operations for SAGE ONE AI work claims.

The file is intentionally dependency-free. Claims are still integrated through
Git: the local operation is atomic within one checkout, and the resulting
ACTIVE_WORK.yaml change must be committed/pushed through the normal PR flow.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATE = Path("coordination/ACTIVE_WORK.yaml")
STALE_HOURS = 24
REQUIRED = (
    "id",
    "agent",
    "branch",
    "base_sha",
    "objective",
    "status",
    "started_at",
    "updated_at",
)


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_claims(text: str) -> list[dict]:
    if "claims: []" in text:
        return []

    claims = []
    current = None
    in_scope = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("  - id: "):
            if current:
                claims.append(current)
            current = {"id": line.split(": ", 1)[1].strip(), "scope": []}
            in_scope = False
            continue
        if current is None:
            continue
        if line.startswith("    scope:"):
            in_scope = True
            continue
        if in_scope and line.startswith("      - "):
            current["scope"].append(line.split("- ", 1)[1].strip())
            continue
        if line.startswith("    ") and ":" in line:
            in_scope = False
            key, value = line.strip().split(":", 1)
            current[key] = value.strip()
    if current:
        claims.append(current)
    return claims


def write_claims(claims: list[dict]) -> None:
    stamp = now()
    lines = [
        "version: 1",
        f"updated_at: {stamp}",
    ]
    if not claims:
        lines.append("claims: []")
    else:
        lines.append("claims:")
        for claim in claims:
            for key in ("id", "agent", "branch", "base_sha"):
                lines.append(f"  - {key}: {claim.get(key, '')}" if key == "id"
                             else f"    {key}: {claim.get(key, '')}")
            lines.append("    scope:")
            for path in claim.get("scope", []):
                lines.append(f"      - {path}")
            for key in ("objective", "status", "started_at", "updated_at"):
                lines.append(f"    {key}: {claim.get(key, '')}")
    data = "\n".join(lines) + "\n"

    STATE.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix="ACTIVE_WORK.",
        suffix=".tmp",
        dir=str(STATE.parent),
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, STATE)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def overlaps(a: str, b: str) -> bool:
    a = a.strip("/ ")
    b = b.strip("/ ")
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def assert_no_overlap(claims: list[dict], scope: list[str], ignore_id: str | None = None) -> None:
    for claim in claims:
        if claim.get("id") == ignore_id:
            continue
        if claim.get("status") not in {"claimed", "in_progress", "blocked", "handoff"}:
            continue
        for left in scope:
            for right in claim.get("scope", []):
                if overlaps(left, right):
                    raise SystemExit(
                        f"OVERLAP: {left} conflicts with active claim "
                        f"{claim.get('id')} ({right})"
                    )


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def stale(claim: dict, hours: int = STALE_HOURS) -> bool:
    try:
        return datetime.now(timezone.utc) - parse_time(claim["updated_at"]) > timedelta(hours=hours)
    except (KeyError, ValueError):
        return True


def command_claim(args: argparse.Namespace) -> None:
    claims = parse_claims(STATE.read_text(encoding="utf-8"))
    if any(c.get("id") == args.id for c in claims):
        raise SystemExit(f"Claim already exists: {args.id}")
    scope = [item.strip() for item in args.scope if item.strip()]
    if not scope:
        raise SystemExit("At least one scope path is required.")
    assert_no_overlap(claims, scope)

    stamp = now()
    claims.append({
        "id": args.id,
        "agent": args.agent,
        "branch": args.branch,
        "base_sha": args.base_sha,
        "scope": scope,
        "objective": args.objective,
        "status": "claimed",
        "started_at": stamp,
        "updated_at": stamp,
    })
    write_claims(claims)
    print(f"CLAIMED: {args.id}")


def command_release(args: argparse.Namespace) -> None:
    claims = parse_claims(STATE.read_text(encoding="utf-8"))
    for claim in claims:
        if claim.get("id") == args.id:
            claims.remove(claim)
            write_claims(claims)
            print(f"RELEASED: {args.id}")
            return
    raise SystemExit(f"Claim not found: {args.id}")


def command_takeover(args: argparse.Namespace) -> None:
    claims = parse_claims(STATE.read_text(encoding="utf-8"))
    target = next((c for c in claims if c.get("id") == args.id), None)
    if target is None:
        raise SystemExit(f"Claim not found: {args.id}")
    if not stale(target):
        raise SystemExit("TAKEOVER BLOCKED: claim is not stale.")
    claims.remove(target)
    scope = target.get("scope", [])
    assert_no_overlap(claims, scope)
    stamp = now()
    claims.append({
        "id": args.new_id,
        "agent": args.agent,
        "branch": args.branch,
        "base_sha": args.base_sha,
        "scope": scope,
        "objective": target.get("objective", ""),
        "status": "claimed",
        "started_at": stamp,
        "updated_at": stamp,
    })
    write_claims(claims)
    print(f"TAKEN OVER: {args.id} -> {args.new_id}")


def command_status(_: argparse.Namespace) -> None:
    claims = parse_claims(STATE.read_text(encoding="utf-8"))
    if not claims:
        print("NO ACTIVE CLAIMS")
        return
    for claim in claims:
        marker = "STALE" if stale(claim) else "ACTIVE"
        print(
            f"{marker} {claim.get('id')} | {claim.get('agent')} | "
            f"{claim.get('branch')} | {', '.join(claim.get('scope', []))}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="SAGE ONE AI work claim control.")
    sub = parser.add_subparsers(dest="command", required=True)

    claim = sub.add_parser("claim")
    claim.add_argument("--id", required=True)
    claim.add_argument("--agent", required=True)
    claim.add_argument("--branch", required=True)
    claim.add_argument("--base-sha", required=True)
    claim.add_argument("--objective", required=True)
    claim.add_argument("--scope", nargs="+", required=True)
    claim.set_defaults(func=command_claim)

    release = sub.add_parser("release")
    release.add_argument("--id", required=True)
    release.set_defaults(func=command_release)

    takeover = sub.add_parser("takeover")
    takeover.add_argument("--id", required=True)
    takeover.add_argument("--new-id", required=True)
    takeover.add_argument("--agent", required=True)
    takeover.add_argument("--branch", required=True)
    takeover.add_argument("--base-sha", required=True)
    takeover.set_defaults(func=command_takeover)

    status = sub.add_parser("status")
    status.set_defaults(func=command_status)

    args = parser.parse_args()
    if not STATE.exists():
        raise SystemExit("coordination/ACTIVE_WORK.yaml is missing.")
    args.func(args)


if __name__ == "__main__":
    main()
