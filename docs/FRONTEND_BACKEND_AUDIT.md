# SAGE ONE Frontend / Backend Audit

Last updated: 2026-10-10

## Audit rules

This is an evidence log, not a claim that the app is end-to-end complete. A screen rendering, a successful build, a static route-contract check, or a route existing in FastAPI does not prove that a live user journey succeeds. Keep automated CI, mocked interaction tests, real-device behavior, and external-provider setup as separate verification categories.

## Latest baseline

- Current main baseline after frontend recovery, navigation, owner-authorization and action-failure regression work: `ff646d0a0767ef927d77598ed7b13abb8f818068`.
- PR #201 frontend recovery and form-validation work merged as `ad769fdc66ed55d098019bdb38634550abbf2f2e`; SAGE CI and Android Release passed.
- PR #202 More-menu navigation and placeholder-action tests merged as `876168e7d85c5e035e31c23523d2e18baa06a16a`; SAGE CI and Android Release passed.
- Latest main SAGE CI run #1702 and Android Release run #282 passed on `ff646d0a0767ef927d77598ed7b13abb8f818068`; Android artifact `11664978073` is available until 2026-10-24.
- PR #192 is merged. It fixed memory dialog controller lifetime, stale-session recovery, project/sales dialog controller lifetime, profile loading lifecycle, and AI Studio workspace validation.
- The route-contract test checks recognized Flutter API paths against FastAPI routes. It is a static contract check, not a live-server integration test.

## Screen-to-backend map

| Screen / entry | Frontend behavior and API methods | Backend route family | Audit status |
|---|---|---|---|
| Splash / app shell | Startup transition; bottom navigation; More menu | No direct API from splash; shell polls notifications | Navigation paths identified; full tap-by-tap test still open |
| Login / Auth Gate / Private Owner Gate | Restore token, sign in, clear stale session, select private owner path | `/identity/config`, `/identity/dev-login`, `/identity/google`, `/identity/me` | Widget tests exist for login and stale-session fallback; Huawei run still required |
| Onboarding | Profile setup, capabilities, OTP UI | `/identity/onboarding/options`, `/identity/onboarding`, `/identity/phone/send`, `/identity/phone/verify` | Backend calls exist; real OTP provider delivery requires external setup |
| Language Selection | Local language selection UI | No direct backend call identified | Persist/restore behavior needs interaction review |
| Command Center | Worker health, submit background task, poll task status | `/worker/health`, `/execute/background`, `/tasks/{task_id}` | API wiring identified; live worker path needs end-to-end test |
| Agent | Submit background task and poll status | `/execute/background`, `/tasks/{task_id}` | API wiring identified; live worker path needs end-to-end test |
| Voice Command | Submit spoken command and poll task | `/command`, `/tasks/{task_id}` | Mock tests exist; physical microphone/speech test pending |
| Voice Mode | Submit background work and poll task | `/execute/background`, `/tasks/{task_id}` | Mock tests exist; physical microphone/STT/TTS test pending |
| Research | Start research, retrieve history/result, inspect task, cancel | `/tools/execute` (research tools), `/execute/background`, `/tasks/{task_id}`, `/tasks/{task_id}/cancel` | Widget coverage exists; source/provider-backed live research not yet device-verified |
| Tasks | List, refresh/poll, cancel tasks | `/tasks`, `/tasks/{task_id}`, `/tasks/{task_id}/cancel` | Widget coverage exists; live worker execution still needs testing |
| Create | Create workspace, project, workflow | `/workflow/workspaces`, `/workflow/workspaces/{id}/projects`, `/workflow/projects/{id}/workflows` | Mock API tests exist |
| Projects | List workspaces/projects and open project detail | `/workflow/workspaces`, `/workflow/workspaces/{id}/projects` | Mock API tests exist |
| Project Detail | Commands, assets, relations, workflow definitions | `/command`, `/workflow/projects/{id}/assets`, `/workflow/projects/{id}/relations`, `/workflow/projects/{id}/workflows` | Mock API tests exist; each action still needs success/error/cancel coverage review |
| Memory | List, review, add, confirm/update, delete memories | `/identity/memory`, `/identity/memory/review`, `/identity/memory/{id}` | Memory review and dialog regression tests exist |
| Owner Console | Owner status/audit and Spark/evolution controls | `/economy/owner/status`, `/economy/owner/audit`, `/economy/owner/spark/*`, `/economy/owner/evolution/*` | Owner-gated backend routes and tests exist; UI error-path coverage needs review |
| Economy | Wallet and premium-work cost reads | `/economy/me`, `/economy/costs` | Mock screen coverage exists |
| Evolution | Wallet/evolution tiers and progress | `/economy/me`, `/economy/evolution/tiers` | Mock screen coverage exists |
| World Intelligence | Status, knowledge, due topics, refresh | `/world/status`, `/world/knowledge`, `/world/due`, `/world/refresh` | Mock coverage exists; mutation owner-check fix is in PR #203 |
| Sales | Leads, lead detail/history, approve outreach, convert, follow-up | `/sales/leads`, `/sales/leads/{id}`, `/sales/leads/{id}/history`, `/sales/leads/{id}/approve-outreach`, `/sales/leads/{id}/convert-customer`, `/sales/leads/{id}/follow-up` | Mock screen coverage exists; live provider/outreach behavior needs validation |
| Spark Wallet | Read balance and ledger | `/economy/me` | Connected read-only surface; no claim of external monetary value |
| Transactions | Display Spark ledger entries | `/economy/me` | Connected to internal ledger data; not a full external payment transaction history |
| Profile | Load and save profile | `/identity/me` GET/PATCH | Form-validation and failure-path regression coverage should be confirmed in CI |
| Settings | Read/update supported profile preferences | `/identity/me` GET/PATCH | API wiring exists; each setting's persistence must be verified |
| Notifications | List, mark one read, mark all read | `/notifications`, `/notifications/{id}/read`, `/notifications/read-all` | Regression tests exist |
| Payments | Read provider status only | `/economy/payment/status` | Intentionally no payment-creation action until a real provider is configured |
| File Manager | Read tasks and display available task artifacts | `/tasks` | Artifact listing is connected; richer file browse/export actions are not established by this screen |
| AI Studio | List/create workflow workspaces | `/workflow/workspaces` | Workspace creation is connected; broader prompt/agent-template features remain incomplete |
| Apps | Buttons show explicit not-connected explanation | No live integration endpoint | Placeholder, truthfully labelled |
| Earnings | Buttons show explicit not-connected explanation | No live earnings endpoint wired from this screen | Placeholder |
| Marketplace | Browse listings, search, publish a listing, send buyer inquiry, view seller inquiries, close own listing | `/marketplace/listings`, `/marketplace/listings/mine`, `/marketplace/listings/{id}/inquiries`, `/marketplace/inquiries/mine` | MVP implementation on `feat/jobs-marketplace-mvp`; automated verification pending. Checkout/payment settlement intentionally not connected |
| Jobs | Browse/search jobs, publish a job, apply, view own postings/applications and close a posting | `/jobs`, `/jobs/mine`, `/jobs/applications/mine`, `/jobs/{id}/applications` | MVP implementation on `feat/jobs-marketplace-mvp`; automated verification pending |
| Learning | Buttons show explicit not-connected explanation | No live learning endpoint wired from this screen | Placeholder |
| Community | Buttons show explicit not-connected explanation | No live community endpoint wired from this screen | Placeholder |
| KYC / Identity Verification | Buttons show explicit not-connected explanation | No provider-backed KYC workflow wired from this screen | Placeholder; provider/legal setup required |
| First Run | Buttons show explicit not-connected explanation | No live setup workflow wired from this screen | Placeholder |

## High-priority frontend remediation (PR #201 — merged)

The merged fix adds retry/error-clearing UI for Spark Wallet, Transactions, Evolution, Notifications, Payments, File Manager, and AI Studio; validation and retained input for project commands, workflow assets, and sales follow-ups; Chat session/history/command recovery with a five-consecutive-failure cap on automatic task-status polling; and exception handling when opening artifact URLs.

The pre-merge PR checks passed: SAGE CI ran 218 Python tests, Flutter analysis, and 61 Flutter tests; Android Release passed analysis, tests, API URL validation, APK build, App Bundle build, and artifact upload. The latest main commit `ff646d0a0767ef927d77598ed7b13abb8f818068` has fresh passing SAGE CI and Android Release runs; its artifact is `11664978073`. These automated checks do not replace physical-device or provider verification.

## Confirmed security fix

World Intelligence refresh and global upgrade-proposal creation now require the authenticated caller's `owner_mode` claim. PR #203 added these checks and regression tests asserting that non-owner claims receive HTTP 403; the owner refresh test is preserved. PR #203 is merged, and its SAGE CI and Android Release runs passed. This is an authorization boundary; it should not be weakened by bypassing the claims check inside the permission engine.

## Runtime and device connection requirements

- Flutter Web / Windows desktop default: `http://localhost:8010`.
- Android emulator default: `http://10.0.2.2:8010`.
- Huawei physical-device development APK: `http://127.0.0.1:8010` with the backend running on the PC and `adb reverse tcp:8010 tcp:8010` active. Alternatively, build with a reachable backend URL.
- The current Android artifact is a private development/testing path using local HTTP, not a production-store release. Production requires deployed HTTPS, production auth/configuration, signing, and release compliance.
- GitHub Pages without a public backend URL can only access a backend reachable from the browser's device.

## Known gaps / external dependencies

- Learning, Community, Apps, Earnings, KYC and First Run actions remain placeholders. Jobs/Marketplace MVP workflows are under implementation in `feat/jobs-marketplace-mvp`; do not treat that branch as deployed to main until its PR merges.
- Payments reports provider status only; no live payment creation/settlement.
- Production SMS/OTP provider and credentials.
- Production Google OAuth/identity configuration and long-lived session UX.
- Full multi-tenant isolation if SAGE becomes a shared public service.
- Broader third-party integrations, permissioned publishing, analytics feedback, and production monitoring/backups.
- Physical Huawei test of owner login, backend connectivity, microphone permission/STT, TTS, app restart/session restore, and task execution.
- Full button-by-button success/error/cancel coverage and visual/reference regression remain in progress.

## Next verification order

1. Complete CI review for `feat/jobs-marketplace-mvp`; verify persistence, validation, and cross-user privacy tests before merging the API/UI work.
2. Extend Jobs/Marketplace Flutter tests for API failure, empty state, duplicate apply/inquiry, and ownership-denied responses.
3. Add Learning and Community real workflows only when their data model and product behavior are defined; keep remaining placeholders clearly labelled.
4. Re-run the screen-to-route contract test and compare every API method against its FastAPI route and response shape.
5. Build the APK from the exact merged `main` commit, record the artifact ID, and install that exact APK on the Huawei phone using the intended API routing (`adb reverse tcp:8010 tcp:8010` for the local-host configuration).
6. On-device, verify sign-in, API connectivity, chat/task execution, memory, notifications, project actions, and microphone/STT/TTS.
7. Only after these checks pass, claim the private demo is end-to-end ready.

