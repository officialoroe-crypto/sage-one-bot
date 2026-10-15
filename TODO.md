# SAGE ONE — TODO

## COMPLETE — CORE RUNTIME
- [x] Durable worker, leases, heartbeat, retry/backoff and recovery.
- [x] Background task API, polling, cancellation and notifications.
- [x] Mission planning, dependency-aware execution and verification.
- [x] Research OS with persistent reports/evidence/claims.
- [x] Provider routing, health visibility and resource protection.
- [x] Unified Chat `/command` execution loop.
- [x] Project-scoped commands and result assets.
- [x] Consent-gated task-experience memory learning.
- [x] Device voice STT/TTS through the durable command path.
- [x] Owner Developer Mode preview/apply safety gate.
- [x] Durable owner-scoped Developer Mode proposals.
- [x] Research and task history/status filtering.

## COMPLETE — IDENTITY / OWNER WORKSPACE
- [x] Authenticated profile persistence.
- [x] Google token validation foundation.
- [x] Phone OTP state machine and provider abstraction.
- [x] Authenticated onboarding entry and first-run completion flow.
- [x] User-visible memory read/add/delete UI.
- [x] Private-first owner entry path + provider-free owner onboarding.
- [x] World Intelligence backend and Flutter status/knowledge/refresh UI.
- [x] Spark reservation/settlement/refund primitives and premium execution lifecycle.
- [x] Evolution achievement settlement and canonical tier API.
- [x] Apps Hub and ecosystem shell surfaces.
- [x] File Manager / AI Studio / Wallet / Payments / Transactions / Profile / Settings / Notifications shell surfaces.

## COMPLETE — PHASE 5 SALES EXECUTION
- [x] Sales discovery and business audit workflow.
- [x] Deterministic lead scoring and durable lead creation.
- [x] Lead intelligence and approval-gated outreach preparation.
- [x] Owner lead activity/history and customer conversion gate.
- [x] Owner Flutter Sales pipeline/detail UI with human follow-up recording.

## REMAINING — EXTERNAL OR DEFERRED
- [ ] Production SMS/OTP provider.
- [ ] Long-lived Google web session refresh UX.
- [ ] Local/provider-backed premium lifecycle smoke test on the user's configured environment.
- [x] Owner-facing consent-driven memory candidate review UX: pending auto-learned memories can be kept or rejected; API client regression tests cover review and confirmation.
- [ ] Full multi-tenant ownership if SAGE becomes public/shared.
- [ ] Broader third-party integrations and permissioned publishing adapters.
- [ ] Analytics → improve feedback loop.
- [ ] Automated Evolution visual regression.
- [x] CI release hardening: Flutter clients share the Android emulator default and the Android APK workflow supports an explicit device API URL (the Huawei workflow default requires ADB reverse).
- [ ] Full button-by-button interaction audit with HTTP-method/path assertions and loading/error/cancel regression coverage.
- [ ] Live backend connectivity smoke test against the configured private environment.
- [ ] Manual Android/device QA (requires physical device/backend access).
- [ ] Resolve physical Android Google Sign-In incident: PR #196 loads and validates server client ID before plugin initialization; a redundant-null-check analyzer failure was corrected in commit `7bd448e722ab6986954b92317d15ed8988961bd2`. Recheck CI on the final head, build with verified phone-reachable API URL, and complete physical-device sign-in before marking fixed.

## DEVELOPMENT CONTROL PLANE
- [x] Machine-readable AI work claims.
- [x] Atomic claim/release and stale-claim detection.
- [x] Handoff records.
- [x] Overlap checks and explicit takeover.
- [x] Compact current-work/status view.
- [x] CI coordination enforcement.
- [x] Pre-PR consistency check: SAGE CI rejects PR branches that do not contain current main.

## VALIDATION
- [x] Python compile/lint/tests on main.
- [x] Flutter analyzer/tests on main.
- [x] Android APK workflow on main.
- [x] God Mode developer website workflow on main.
- [ ] Manual full-device walkthrough.
- [ ] Full visual/reference comparison.

## PRINCIPLE
Do not mark an item complete because code exists alone. Mark it complete when the runtime path is real and the relevant verification evidence exists.
