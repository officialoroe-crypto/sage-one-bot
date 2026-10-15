# SAGE ONE — DEVELOPMENT RULES

## Coding Workflow

1. Inspect before changing.
2. Never rebuild working components.
3. Prefer bulk changes.
4. Prefer complete replacement files.
5. Give exact Windows paths.
6. Give exact commands.
7. Keep manual edits minimal.
8. Test after meaningful changes.
9. Record important state changes in `PROJECT_STATE.md`.
10. Keep `CHANGELOG.md` updated for major milestones.
11. Before calling a feature complete:
    - trace the full request/auth/execution/result flow
    - identify why it works and what can break
    - verify refresh/restart behavior
    - verify failure/retry behavior
    - run the relevant tests and deployment checks
    - only then mark the feature complete

## Resource Rules

The laptop must remain usable.

Heavy:
- AI inference
- deep research
- multi-source reading
- synthesis
- verification
- long-running jobs

should eventually run in cloud/background workers.

Do not automatically invoke local Ollama for heavy work.

## Reliability Rules

Never hide failures.

Every task should have an explicit state such as:
- pending
- running
- retrying
- completed
- failed
- dead

Long-running work must be recoverable.

Worker execution should be idempotent.

## Research Rules

Preserve provenance.

Every extracted evidence item should eventually be traceable to:
- source
- URL
- relevant passage/content
- retrieval context
- claim/evidence relationship

Avoid unnecessarily huge prompts and outputs.

## Chat Continuity Rule

The code repository is the source of truth.

`PROJECT_STATE.md` is the continuity summary.

At the end of major development sessions:
- update project state
- update TODO
- update CHANGELOG when appropriate

When a new ChatGPT conversation starts, provide/read the current state rather than rebuilding from memory.
