# SAGE ONE — AI WORK CONTROL PLANE

This directory is the machine-readable coordination state for independent AI sessions working on the repository.

## Protocol
- `ACTIVE_WORK.yaml` contains active claims.
- A claim reserves its declared path/module scope.
- Agents must inspect `main` and this file before editing.
- Exact-path overlap is forbidden while a claim is active.
- Parent-directory overlap is treated conservatively: e.g. `execution/` overlaps `execution/engine.py`.
- Claims are not permission to merge; PR + CI remains required.
- Human can release, reassign, or override a claim.
- Stale claims require explicit takeover; do not silently steal work.

## Agent handshake
1. Read `PROJECT_STATE.md`, `TODO.md`, `AI_COLLABORATION.md`, and `coordination/ACTIVE_WORK.yaml`.
2. Inspect latest `main` SHA.
3. Claim a non-overlapping scope.
4. Work only inside the claim unless the claim is updated first.
5. Before PR, record changed files, tests, failures, and next action.
6. After merge/handoff, release the claim.

## Operational controls
Use `python coordination/claims.py status` to inspect claims.

Create a claim before editing:
`python coordination/claims.py claim --id <id> --agent <agent> --branch <branch> --base-sha <sha> --objective "<objective>" --scope <path> [<path> ...]`

Release after merge/handoff:
`python coordination/claims.py release --id <id>`

Takeover is explicit and only allowed after a claim is stale:
`python coordination/claims.py takeover --id <old-id> --new-id <new-id> --agent <agent> --branch <branch> --base-sha <sha>`

The claim helper rejects exact-path and conservative parent-directory overlap. It writes the state atomically within a checkout; the state change must still be committed/pushed through the normal PR flow.

Claims do not grant permission to merge or execute runtime actions. GitHub PR + CI and SAGE runtime permissions remain separate controls.
