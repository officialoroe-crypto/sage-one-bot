# MISTAKES AND PREVENTION

This is a durable learning log. Record recurring mistakes with a prevention rule.

## Format

### [DATE] — Short mistake name
- What happened:
- Why it happened:
- Prevention:
- Scope:
- Status:

## Initial prevention rules

### 2026-09-27 — Do not treat the memory system as ChatGPT-only
- What happened: The first design was framed primarily as a ChatGPT working manual.
- Why it happened: The need for the same durable interaction contract inside future SAGE ONE was not fully captured.
- Prevention: Maintain a shared memory contract readable by both the owner-facing ChatGPT workflow and SAGE ONE, while keeping actual private conversation memory in SAGE ONE's private storage.
- Scope: Global owner-memory architecture.
- Status: Resolved by the current memory model.


### 2026-10-10 — Windows Git Bash cannot assume ADB is on PATH
- What happened: Running `adb devices` returned `bash: adb: command not found`, even though Android SDK platform-tools and a connected phone were present.
- Why it happened: The SDK's `platform-tools` directory is not on this Git Bash session's PATH.
- Prevention: Use the verified executable path `/c/Users/Nishant/AppData/Local/Android/Sdk/platform-tools/adb.exe` in commands, or configure PATH deliberately after confirming the SDK path. Clearly label expected output as an example and tell the owner not to paste output lines as commands.
- Scope: Local Android debugging on the owner's Windows/Git Bash environment.
- Status: Resolved for this session; ADB found the authorized phone and USB reverse mapping for port 8000 was confirmed.


### 2026-10-10 — Blank phone caused onboarding 422
- What happened: Memory Setup reached POST /identity/onboarding and backend returned HTTP 422 with a message that phone must contain at least five characters.
- Why it happened: Shared identity client could serialize a blank phone string even though private Owner Mode allows skipping phone at this stage.
- Prevention: Omit null/blank optional phone values and trim nonblank values; add regression coverage and verify the real website/backend response.
- Scope: Shared Flutter web/mobile onboarding.
- Status: Client fix merged in PR #214; automated CI passed before merge. Actual website flow still needs verification.

### 2026-10-11 — Treat every response as a continuity checkpoint
- What happened: Owner had to repeat the requirement to save context and next steps, risking lost project state between replies.
- Why it happened: Memory updates were treated as occasional/manual rather than a mandatory close-out step.
- Prevention: After each assistant reply in active work, save relevant context, decisions, causes, fixes, evidence, unresolved work, and next action. Keep public notes privacy-safe and disclose any failed/unavailable memory write.
- Scope: Owner-facing workflow and SAGE ONE memory contract.
- Status: Rule documented; persistence still depends on connected tools and successful writes.
