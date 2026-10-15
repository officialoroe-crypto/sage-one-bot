# SAGE ONE — CHANGELOG

## 2026-10-08 — Session 4 Production Hardening / Android Release Validation
- Hardened the Android release workflow with bounded runtime, concurrency cancellation, and Flutter dependency caching.
- Validated the configured Android-reachable backend URL before building and rejected URLs containing embedded credentials.
- Added release App Bundle generation alongside the release APK.
- Published both Android release artifacts with 14-day retention.
- Expanded regression coverage for the Android release workflow contract.
- Kept production signing/keystore configuration, store publishing, and physical-device QA explicitly deferred until real credentials and device/backend access are available.

## 2026-09-22 — Full Repository Audit / Security Hardening
- Audited all Python and Flutter/Dart source files in the current repository tree with CI compilation, linting, tests, and targeted source scans.
- Made verified Evolution settlement transactional and idempotent.
- Restricted global permission mutations and legacy permission audit access to SAGE Owner Authority.
- Redacted task results/errors from the public worker health endpoint and added authenticated diagnostics.
- Enforced a configured single-owner boundary for production deployments.
- Added a Huawei P40 development APK path using a configurable SAGE API endpoint and documented ADB reverse networking.
- Fixed a real main-branch heartbeat test failure by removing scheduler timing dependence from the regression test.
- Current remaining production items are tracked in `TODO.md`: SMS provider, long-lived Google session refresh, Spark settlement integration, and future multi-tenant isolation.

## 2026-09-21 — Full Code Audit
- Hardened verified-achievement settlement rollback so any post-flush failure rolls back the entire transaction.
- Removed duplicate atomic-settlement regression coverage and an accidental empty root file.
- Added explicit regression coverage proving a failed settlement leaves both the evidence event and Evolution state unchanged.

## 2026-09-18 — Provider Routing v2
- Added deterministic LIGHT / MEDIUM / HEAVY provider routing.
- Made Groq the first cloud provider in automatic routing.
- Kept Cerebras as secondary cloud fallback.
- Restricted automatic Ollama use to light work with safe local resources.
- Added explicit `auto`, `cloud`, and `local` routing modes.
- Added CPU-aware routing decisions and routing diagnostics.
- Added regression tests for routing and local CPU protection.

## 2026-09-17 — Background Task API
- Added durable `POST /tasks` queue creation.
- Added task listing with status filtering.
- Added task lookup and cancellation endpoints.
- Added standalone `python -m app.background_worker` entry point.
- Reconnected the worker to local resource protection so busy CPU defers queued work.
- Added regression coverage for the task API and resource-protection path.

## 2026-09-17

### Research OS
- Search system confirmed working.
- Multiple-query search works.
- Deduplication works.
- Source IDs, URLs, snippets, provenance and timestamps are present.
- Previous test produced 6 unique sources from 3 queries.
- Web Reader / research synthesis work has progressed to reading multiple sources and producing evidence items.

### CI
- GitHub-hosted CI compiles Python modules and runs the full pytest suite.
- Repository-root import configuration is established in CI.

### Worker Architecture
- Durable worker lifecycle implemented with atomic claiming, ownership, leases, heartbeats, retry/backoff and recovery.
- Worker execution now passes ownership context into the orchestrator.

### Performance Architecture
- Recent tests pushed the laptop CPU to approximately 100%.
- Heavy AI/research work is therefore designed for cloud/background execution.
- Local Ollama must not automatically become the fallback for heavy work.
- SAGE classifies tasks as LIGHT / MEDIUM / HEAVY.
- Local resource protection is active.

## Earlier Known Milestones

### Backend
- FastAPI/Uvicorn backend established.
- Backend has been run on port 8010 using the project virtual environment.
- Database initialization produced:
  `SAGE DATABASE INITIALIZED.`

### Flutter
- Flutter stable environment configured.
- Flutter doctor was previously green.
- Multiple connected devices were available.

### Gemini
- An unavailable Gemini model name caused a 404.
- Later Gemini usage encountered free-tier request quota limits.

### Ollama
- `llama3.2:3b` produced an empty summary / 0 claims during reliability testing.
- This contributed to restricting local Ollama to controlled light workloads.
