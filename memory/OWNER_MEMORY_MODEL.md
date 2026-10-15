# OWNER MEMORY MODEL

## Goal

SAGE ONE should feel personal because its memory is **identity-scoped**, not because all users share one global memory.

## Current mode: single owner

During private-first development:

- There is one owner identity.
- Owner memory is the authoritative personal memory scope.
- Owner preferences and interaction history are loaded for the owner-facing assistant.
- Project memory can be linked to the owner without becoming global public memory.
- Developer/owner mode does not imply authority over external systems.

## Future multi-user mode

If additional users are added:

`GLOBAL → USER → PROJECT → CONVERSATION → TASK`

Each layer has a scope.

### GLOBAL

Safe product-wide rules and architecture. No owner-private preferences.

### USER

A user's own preferences, profile, durable memories, conversation summaries, and permissions.

### PROJECT

Project context belonging to the user or an explicitly shared workspace.

### CONVERSATION

Conversation-specific context and summaries.

### TASK

Temporary execution state, artifacts, tool results, and verification evidence.

## Owner-only data

Owner-only data must include an explicit owner/user scope in storage and retrieval. Never query personal memory with an unscoped global lookup.

Recommended conceptual key:

`memory(owner_id, scope, category, key, value, confidence, source, created_at, updated_at)`

The exact implementation may evolve, but **ownership must be enforced at the data-access boundary**, not only by the UI.

## Memory write policy

Not every message becomes memory.

Persist when the owner:
- establishes a durable preference;
- makes an explicit decision;
- corrects a recurring behavior;
- creates or changes a project constraint;
- provides durable personal context needed for future work;
- completes a milestone that affects future execution.

Do not persist:
- transient conversation chatter;
- one-off guesses;
- secrets;
- credentials;
- unnecessary sensitive data.

## Retrieval policy

Retrieve memory relevant to the current task, not the entire history.

Use:
1. identity scope;
2. task/project scope;
3. recency;
4. relevance;
5. confidence/source quality.

The assistant should be able to explain internally which memory items influenced an action.

## Privacy boundary

This GitHub repository is public. It contains the **memory contract and safe durable project documentation**, not private owner conversation records.

Private owner memory belongs in the SAGE ONE private database/storage layer.
