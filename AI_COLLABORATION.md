# SAGE ONE — AI COLLABORATION & WORK-LOCK PROTOCOL

## Purpose
SAGE ONE may be developed from multiple independent AI sessions/accounts. Hidden chat history is not a synchronization mechanism. GitHub is the shared source of truth.

This protocol prevents simultaneous edits, stale-context overwrites, duplicated implementation, undocumented handoffs, and unverified completion claims.

## Source of truth
1. GitHub `main` is the canonical integrated state.
2. A feature branch is the canonical state of one active work item.
3. A PR is the integration boundary.
4. Chat conversation is context, not authoritative project state.
5. `PROJECT_STATE.md`, `TODO.md`, and this file are shared development memory.

## Mandatory AI preflight
Before editing, every AI must: inspect the latest `main` SHA; read `PROJECT_STATE.md`, `TODO.md`, and this protocol; check open PRs/issues and active work claims; inspect Git history and target files; create/update a work claim; and stop if the intended scope overlaps an active claim.

## Work claim
```yaml
id: unique-work-id
agent: chatgpt | other-ai | human
branch: feature/example
base_sha: full-main-sha
scope:
  - path/or/module
objective: concise objective
status: claimed | in_progress | blocked | handoff | ready_for_review | complete
started_at: ISO-8601
updated_at: ISO-8601
```

For now, claims live in GitHub issues/PRs plus the coordination record. A later implementation may add machine-readable `coordination/ACTIVE_WORK.yaml` and automated overlap checks.

## Editing rules
- One active claim owns a file/module scope at a time.
- Prefer disjoint scopes for parallel AI work.
- Never assume another AI finished because its chat stopped.
- Before commit, compare the branch with current `main` and inspect changed files.
- If another agent changed the same file since branch creation, stop and reconcile intentionally.
- Never force-push. Use feature branches and PRs.
- Never overwrite another agent's work merely to make tests pass.

## Handoff contract
Every completed or paused work item must leave: branch, latest commit SHA, files changed, tests/CI status, known failures, remaining work, protected files, and exact next action.

## Safe parallelism
Parallel work is allowed only when scopes are genuinely disjoint. Example: AI A edits `agentic/*` while AI B edits Flutter UI. Unsafe: both edit `execution/engine.py` or the same database model.

## Integration rule
Only integrate through PR review/CI. If a branch is stale, update it from `main` safely before integration. Resolve conflicts by understanding both changes, not by blindly choosing one side.

## Automated PR base consistency guard
SAGE CI runs a preflight on pull requests. It fetches current `origin/main` and the PR head, then verifies that current main is an ancestor of the PR branch. If main has advanced past the branch, CI fails with an explicit instruction to update the branch. This prevents stale-base integration from silently reaching merge.

## Runtime vs developer coordination
This is a developer collaboration control plane, separate from SAGE's runtime Permission Engine. Runtime permission determines whether SAGE may perform an owner action; developer locks determine whether an AI may edit a project scope.

## Planned automation
1. Machine-readable active claims.
2. Atomic claim/release.
3. Path-overlap detection.
4. Stale-claim detection and explicit takeover.
5. Handoff records.
6. Pre-PR consistency checks — enforced in SAGE CI by verifying current main is an ancestor of the PR head.
7. CI enforcement for stale PR bases — implemented.
8. Compact current-work status usable by any AI.

The goal is that a second AI can join the repository, understand current state, see locks, choose safe work, and continue without needing this conversation.
