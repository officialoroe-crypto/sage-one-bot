# SAGE ONE Memory System

This directory defines the persistent memory and interaction model shared by the owner-facing SAGE ONE system and compatible AI workflows.

## Core idea

SAGE ONE is currently a **single-owner personal AI**. The owner's interaction preferences, working style, decisions, corrections, and durable context belong to the owner profile and must not become shared defaults for other users.

This repository is the **documentation/source-of-truth for the memory contract**. Private conversation history and sensitive personal memory must be stored in the SAGE ONE private memory store, not committed to this public repository.

## Memory layers

- `CHATGPT_OS.md` — how an AI should work with the owner.
- `OWNER_MEMORY_MODEL.md` — how SAGE ONE should separate owner memory from other users.
- `RULES.md` — durable behavioral rules.
- `PREFERENCES.md` — stable communication and workflow preferences.
- `DECISIONS.md` — explicit owner decisions and constraints.
- `MISTAKES.md` — mistakes, root causes, and prevention rules.
- `CURRENT_CONTEXT.md` — current cross-project context that is safe to keep in the public repository.
- `projects/` — project-specific durable context.

## Privacy rule

Do not store raw chats, secrets, credentials, private contact details, authentication material, or sensitive personal information in this public repository. SAGE ONE's private memory database should hold those records.

## Update rule

When the owner gives a durable instruction, correction, preference, or decision, classify it and update the appropriate memory layer. Do not create duplicate contradictory rules; preserve the newest explicit owner decision and record superseded decisions when useful.
