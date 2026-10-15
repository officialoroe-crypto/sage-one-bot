# SAGE ONE — SHARED AI WORKING CONTEXT

Last updated: 2026-10-01

## Current milestone
SAGE ONE completed the first major Agentic Action Gateway integration: Agentic Action Engine implemented and merged; Core/direct tool execution routed through the Action Engine; mission-level tool execution routed through the Action Engine. Main: `a3f82b7deb10ae8346fa422d3a8e87a46ae8b285`. PRs #87, #88, and #89 are merged.

## Core completion target
Do not declare the core complete until this lifecycle is traceable:
REQUEST → PLAN → ACTION → PERMISSION → TOOL → EXECUTE → VERIFY → EVIDENCE → RESULT → SETTLE → EVOLUTION → HISTORY

Next core pass: tighten action/task/mission correlation; authorization provenance; action verification vs real outcome verification; first-class evidence; traceable final result/history; and success/failure/restart/regression tests.

## Important architecture rules
- Tool execution must go through the controlled Action Engine; no arbitrary callable paths.
- Permission is fail-closed. Capability is not permission.
- Tool success is not automatically proof that the user's intended outcome happened.
- Evidence should be first-class.
- Runtime Permission Engine and developer AI collaboration locks are separate concerns.
- Durable Automation is distinct from the bounded local execution scheduler.
- Spark is the platform currency at 1 Spark = NPR 1 (owner decision 2026-10-11). Cash-out is disabled until a provider, owner opt-in and legal review exist.
- Heavy AI inference should remain cloud-first for the current development laptop.
- Voice comes after the text execution loop.
- Flutter should first expose the real SAGE interaction loop rather than many disconnected screens.
- World Intelligence must remain source-backed and must not self-modify SAGE.

## Multi-AI collaboration decision
Multiple AI accounts may work on the same repository, but they must never rely on shared chat memory. GitHub is the shared source of truth. Each AI must preflight from latest main, claim a scope, avoid overlapping locks, record branch/base SHA/objective, record changes and validation, hand off explicitly, integrate through PR + CI, and stop/reconcile when overlap is detected. Canonical protocol: `AI_COLLABORATION.md`.

## Immediate work queue
1. Continue SAGE Core integration/regression hardening.
2. Add World Intelligence source-quality/domain policy.
3. Add consent-driven memory auto-learning pipeline.
4. Complete Flutter Command Center against the real execution loop.
5. Add automated Evolution visual regression coverage.
6. Later: voice, device/computer control, public-release preparation.

## Development style
Work in large logical batches. Inspect first, implement coherent changes, validate in one consolidated pass. Keep active-work user updates concise.


## Verified current state — 2026-10-01
- Standard Tool Contract metadata is implemented and merged.
- Durable Automation Engine is implemented and merged; schedules enqueue normal durable tasks and never bypass Action Engine permissions.
- Automation trigger events are persisted.
- Outcome verification events are persisted separately from tool action identity.
- Durable execution evidence has a controlled read surface.
- Mission trace/result endpoints require SAGE Owner Authority.
- AI collaboration claims are operational through `coordination/claims.py`, with overlap/stale checks and CI validation.
- Current main SHA: `a3f82b7deb10ae8346fa422d3a8e87a46ae8b285`.
- The 13 Evolution System remains a locked product/design constraint; backend work must not silently redefine its rank names, visual identities, or progression rules.
