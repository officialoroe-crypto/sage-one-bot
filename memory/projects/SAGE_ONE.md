# SAGE ONE — MEMORY INTEGRATION

## Role

SAGE ONE is the implementation target for the shared owner-memory contract.

## Current identity

- Assistant: sage.ai
- Mode: private-first owner mode
- Primary use: one owner before any public multi-user release

## Integration requirements

SAGE ONE should consume the memory contract in `memory/CHATGPT_OS.md` and `memory/OWNER_MEMORY_MODEL.md`.

The runtime memory layer should provide:
- owner-scoped retrieval;
- structured durable memory;
- conversation summaries;
- project-scoped memory;
- explicit memory provenance;
- memory update/write operations;
- user isolation before multi-user mode is enabled.

## Important distinction

The GitHub files define the **rules and schema**.

The SAGE ONE runtime/database should contain the **private data**.

Do not make the public Git repository the database for the owner's private conversations.

## Future conversation continuity

A new SAGE ONE conversation should be able to load a compact relevant context package such as:

`OWNER PROFILE + DURABLE RULES + RELEVANT PROJECT MEMORY + RECENT CONVERSATION SUMMARY + ACTIVE TASK STATE`

It should not blindly load the entire conversation archive into every request.


## Current execution checkpoint — Android Google sign-in (2026-10-10)

### Verified from the user's local terminal
- The SAGE ONE backend responds at `http://127.0.0.1:8000`.
- `GET /openapi.json` returned HTTP 200 and identified the API as SAGE ONE version `6.0.0`.
- `GET /identity/config` returned `success: true`, a Google client ID is configured, `developer_mode: true`, and `owner_mode_available: true`. Do not copy the client ID into public memory; record only that it is configured.
- ADB is installed at `C:\Users\Nishant\AppData\Local\Android\Sdk\platform-tools\adb.exe`. Git Bash does not have `adb` on PATH, so use the absolute path unless PATH is intentionally fixed.
- The Huawei P40 Pro is connected and authorized. ADB listed one device with status `device`.
- The user successfully ran `adb reverse tcp:8000 tcp:8000`; `adb reverse --list` returned `usb tcp:8000 tcp:8000`. The USB reverse mapping is confirmed for this session.

### What is and is not proven
- Proven: backend availability, identity config availability, ADB device authorization, and USB port reverse mapping.
- Not yet proven: APK is installed, the app is using port 8000, Google sign-in succeeds on the physical phone, token exchange succeeds, or owner-authenticated API calls work.
- A successful CI build is not proof of real-device login.

### Safe next steps
1. Keep avoiding local Flutter/Gradle builds while the laptop is hot or CPU usage is high. Prefer GitHub Actions-built APKs.
2. Before selecting or dispatching an APK build, inspect the Android workflow's `api_url` input and ensure the APK is configured for `http://127.0.0.1:8000` when using this USB reverse mapping.
3. Install only an artifact whose build configuration is verified; then launch it and test Google sign-in on the connected Huawei.
4. Capture the exact outcome/errors, then verify authenticated identity/API behavior before marking sign-in complete.
5. Continue in bulk mode with clear evidence-based status; do not claim a step passed unless its output confirms it.

### Current next action
The user said they will provide code so development can continue. Review the code they provide, identify the relevant SAGE ONE area, and proceed from this checkpoint without repeating completed checks.


## Mandatory assistant continuity checkpoint
Owner explicitly ordered that each assistant reply in the active workflow must be followed by a saved continuity update without another reminder. Follow memory/RULES.md. After each response, update this project checkpoint and memory/CURRENT_CONTEXT.md as appropriate, including current goal/constraints, work done and PR/commit/workflow links, verified versus assumed status, symptom/root cause/fix, failed or unverified checks, and next action with acceptance criteria. Never claim persistence if the write did not succeed. Keep public memory free of raw private transcripts, secrets, tokens, and sensitive owner data; if memory tools are unavailable, disclose the limitation and provide a portable checkpoint.

## Current checkpoint — Website onboarding first (2026-10-11)
- User chose to pause mobile app testing and finish website verification first.
- Backend logs supplied by owner: GET /identity/config 200; POST /identity/dev-login 200; POST /identity/onboarding 422 twice.
- Screenshot showed Memory Setup with a validation error requiring phone to have at least five characters. Exact request body was not captured.
- Cause found in shared frontend/lib/core/identity_client.dart: a blank phone string could be included in the onboarding JSON.
- PR #214 fixed this by omitting null/blank phone and trimming nonblank values; merged to main at dcd9de554a80dbcff18785228145ed414b77f8f6. https://github.com/officialoroe-crypto/sage-one/pull/214
- Pre-merge CI run #38055455236 passed Flutter analysis/tests and Android artifact build. This is not browser verification.
- Android workflow run #38056491244 was seen in progress after merge; do not resume mobile until website checks pass.
- Website: https://officialoroe-crypto.github.io/sage-one/
- Still unverified: Pages deployment includes merged code; blank-phone onboarding returns 200; key pages/buttons work; Google sign-in works. Developer mode may route to Owner Mode.
- Next actions: verify latest Pages deployment, hard-refresh website, test onboarding with phone blank, confirm backend returns 200; inspect Network response if 422. Then test primary navigation, profile/memory consent, relevant buttons/links, and Google login separately. Only then resume Android.

## Current checkpoint — Public marketing website launch (2026-10-11)
- Owner authorized creation and launch of the public SAGE ONE marketing website using a free deployment path, auditing the repository first and avoiding duplicate work.
- Audit found the existing static landing page in `website/`; it was not necessary to create a second website. Existing Pages workflow previously deployed only the Flutter app at the root, which would conflict with the marketing page.
- PR #218: https://github.com/officialoroe-crypto/sage-one/pull/218 (branch `feature/public-marketing-site-launch-20261011-v2`).
- Changes: SEO/Open Graph metadata, orbital favicon, public CTA to the app path, honest wording that some features are still in development, reduced-motion/accessibility fallback, combined artifact layout with marketing page at `/sage-one/` and Flutter app at `/sage-one/app/`, automatic main deployment on website/frontend changes, and PR validation separated from protected deployment.
- CI status when checked: PR workflow run #185 initially failed with no job steps/logs available through the connector; likely environment/job initialization issue, not yet root-caused. Workflow was then refactored into separate build and deploy jobs in commit `e99bb5380ea36f70a1085c9a87221cf8359e0b4f`. No workflow run was yet visible for this latest commit at the last check.
- Not verified: passing CI, merged PR, GitHub Pages configuration, successful deployment, live page rendering, or app deep link. Do not say the site is launched until verified.
- Next: retrieve fresh PR checks for latest head, fix any actual CI failure, merge only after checks pass, then confirm deployment URL and test landing page plus `/app/` route. Do not resume Android until website verification is complete.

## Latest website launch status — 2026-10-11
- The first website launch PR #217 was closed because its branch fell behind main while the required continuity checkpoint was saved. No work was discarded; changes were reapplied on a fresh branch based on current main.
- Active PR #218: https://github.com/officialoroe-crypto/sage-one/pull/218, branch `feature/public-marketing-site-launch-20261011-v2`.
- Current Actions: website workflow run #187 was cancelled because its shared concurrency group conflicted with another workflow. The workflow now uses an isolated `sage-one-public-pages` group; latest website workflow run #190 is queued. SAGE CI run #1797 is queued and Android Release run #341 is pending. No latest run has completed yet.
- A prior PR workflow attempt failed before steps/logs were available; the workflow was refactored to separate build validation from protected deployment. Latest run #190 is queued after isolating Pages concurrency; no successful build or deployment result is available yet.
- Deployment remains unverified. Do not merge until required checks pass; then verify GitHub Pages deployment and the `/sage-one/` marketing page plus `/sage-one/app/` link.


## Latest website launch checkpoint — 2026-10-10
- Owner reaffirmed that making the SAGE ONE web application live is the top priority; laptop is lagging with Opera/ChatGPT consuming substantial CPU. Avoid local Flutter/Gradle builds and use GitHub Actions; suggested checking Opera's task manager (Shift+Esc where supported), closing unnecessary tabs/extensions, and Windows Task Manager sorted by CPU.
- PR #218 merged successfully into `main` using squash merge: https://github.com/officialoroe-crypto/sage-one/pull/218. Merge commit: `3d951d2c7ffb3ed1d1ec70edb64c09d29432f4b4`.
- Verified PR-head SAGE CI run #1801 succeeded: https://github.com/officialoroe-crypto/sage-one/actions/runs/38058424862.
- Verified PR-head public website workflow run #192 succeeded: https://github.com/officialoroe-crypto/sage-one/actions/runs/38058424871. Flutter pub get, analyze, tests, web build under `/sage-one/app/`, and combined site packaging all passed. Upload/deploy steps were correctly skipped on pull_request.
- Not yet verified: post-merge GitHub Pages deployment run, actual public page rendering, app deep link, or browser onboarding/auth flows. Attempts to access the live URLs via the available web fetch were blocked/unavailable, which is not proof the URLs are down.
- Intended URLs remain https://officialoroe-crypto.github.io/sage-one/ (marketing site) and https://officialoroe-crypto.github.io/sage-one/app/ (web app). Do not call launch complete until a main-branch Pages deployment succeeds and the owner/browser confirms both URLs.
- Next: inspect GitHub Actions deployment on main / Pages settings; then verify both URLs. Only after website verification resume onboarding/button checks and later Android Google sign-in. Do not use local heavy builds while CPU is high.


## Backend connection diagnosis — 2026-10-10
- Owner ran `curl -i http://127.0.0.1:8010/identity/config`; curl returned error 7, could not connect. `netstat -ano | findstr :8010` produced no visible output, consistent with no process listening on port 8010 at that time.
- This establishes that the local endpoint is unreachable; it does not yet establish whether the intended backend should run on 8010 or whether the public Pages app is mistakenly configured to call localhost.
- Next: ask owner to list `C:\SageOne` and `C:\SageOne\Backend` (Git Bash: `cd /c/SageOne && ls`, then `ls /c/SageOne/Backend`) to identify actual local checkout/backend structure and startup instructions. Do not run a local Flutter/Gradle build; CPU is already high. If the error is from the public deployed web app, localhost is the visitor's machine and production must use a reachable HTTPS backend URL.


## Backend folder discovery — 2026-10-10
- Owner's Git Bash listing confirms `C:\SageOne` contains `Backend/`, `desktop-agent/`, `img-assets/`, `sage_core-android-signin-test/`, `Git/`, `docs/`, `sage_core/`, and `sage_one/`.
- `C:\SageOne\Backend` contains `app/`, `memory/`, and `venv/`. This identifies a local backend environment but not yet its startup entrypoint, dependencies, or intended port.
- The last connection check still showed no listener at `127.0.0.1:8010`. Previous context says backend had responded on port 8000; check port/config rather than assuming 8010 is correct.
- Next low-cost diagnostic: list `C:\SageOne\Backend\app` and locate dependency/startup files (`requirements.txt`, `pyproject.toml`, `run*.bat`, `main.py`, `uvicorn` instructions) without activating the venv or running a build. Still need to establish whether the reported browser error is from local app or public GitHub Pages app; public deployment must never call localhost for shared users.


## Public web API root cause confirmed — 2026-10-10
- Owner confirmed the `ERR_CONNECTION_REFUSED` was on the public GitHub Pages app (`A`); local app (`B`) has not been opened.
- Inspected `frontend/lib/core/identity_client.dart` and `frontend/lib/core/sage_api.dart` on main. Both use `String.fromEnvironment('SAGE_API_URL')`, but when unset their web default is hardcoded to `http://localhost:8010`.
- This is a confirmed production configuration defect: for a public visitor, localhost points to that visitor's computer. The local curl failure on the owner's machine is separate and cannot fix the public app.
- GitHub Pages workflow `.github/workflows/sage-one-god-mode-pages.yml` only builds and deploys static marketing + Flutter web assets; no backend service is deployed by this workflow. Therefore fixing frontend configuration alone requires a real reachable HTTPS API endpoint. Do not replace localhost with an invented URL, and do not claim the app is working until backend hosting/configuration and live smoke tests succeed.
- Next: inspect repository for any already configured backend host/service and deployment docs/workflows. If none exists, choose a no-card/free-tier HTTPS backend host compatible with FastAPI and persistent database needs, explain any limits, deploy safely without exposing secrets, pass `--dart-define=SAGE_API_URL=https://...` to the Pages Flutter build, then verify `/identity/config`, CORS, authentication/onboarding, and public browser behavior. Avoid local heavy builds due laptop CPU.


## Backend and web deployment checkpoint — 2026-10-11
- Local `GET http://127.0.0.1:8000/identity/config` confirmed HTTP 200 with success/developer-mode/owner-mode flags true. This is a local endpoint check only; Google sign-in/onboarding remain unverified.
- Confirmed Pages workflow builds Flutter web without a SAGE_API_URL dart-define and deploys static assets only. No root README, render.yaml, railway.json, fly.toml, or root backend requirements file was found at the checked paths; further repo inspection is required before concluding no existing host setup exists.
- Public app still has confirmed fallback to localhost:8010 when SAGE_API_URL is unset. Do not claim production app works until a real HTTPS backend URL is configured and live checks pass.


## PR 220 checkpoint — 2026-10-11
PR #220 adds a public deployment guard requiring HTTPS SAGE_API_URL and passes it to Flutter web builds. It also documents backend host configuration, durable PostgreSQL, CORS and OAuth env. CI runs #196, #357 and #1836 were pending at checkpoint. No real API host, database, repository variable, merge, or live verification yet; do not call the public app fixed.


## Public localhost error update — 2026-10-11
- Browser console confirms `localhost:8010/identity/config` fails with `net::ERR_CONNECTION_REFUSED` on the public app. This matches the known production defect: without `SAGE_API_URL`, Flutter web points to the visitor's own machine.
- PR #220 remains open: https://github.com/officialoroe-crypto/sage-one/pull/220. SAGE CI run #1836 passed; public website PR validation run #196 passed and skipped deploy as expected; Android Release run #357 was still building APK at last check.
- No hosted HTTPS API URL, durable production database, or repository `SAGE_API_URL` Actions variable is configured yet. Do not call the public web app fixed. Next: complete PR synchronization/checks, then host backend and configure actual URL before a main-branch Pages deployment and live auth/onboarding tests.


## Backend deployment walkthrough — 2026-10-11
- Owner says the marketing/web site is already deployed and wants step-by-step instructions to deploy the missing backend. Avoid local Flutter/Gradle builds.
- Candidate host: Render. Official docs support free FastAPI web services, but free services spin down after 15 minutes and have ephemeral filesystems; free Render Postgres expires after 30 days. Free DB is unsuitable as durable production storage for real SAGE ONE user data.
- Service settings: repo `officialoroe-crypto/sage-one`, branch `main`, Python 3, root blank, build `pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, health `/health`. Env: `SAGE_ENV=production`, `SAGE_PRIVATE_MODE=false`, `SAGE_DEV_MODE=false`, `SAGE_CORS_ORIGINS=https://officialoroe-crypto.github.io`, private `GOOGLE_CLIENT_ID`. `SAGE_DATABASE_URL` must point to a durable DB before real user data; SQLite can be used only for temporary smoke test if backend initializes without explicit DB URL.
- PR #220 remains open and currently reports `mergeable=false` at head `f67d31e501920a6469ed7bb0889b5b1bbb98ed6c`; branch likely needs sync after main checkpoint writes. Last verified SAGE CI and website PR build passed; Android release APK build was still running.
- Next: user deploys backend and shares its public HTTPS base URL only. Test `/health`, `/identity/config`, configure GitHub Actions variable `SAGE_API_URL`, synchronize/merge PR #220 after CI, deploy Pages and verify browser API calls/auth/onboarding.


## PR #220 merged — 2026-10-11
- Owner authorized merge after confirming the PR was ready. PR #220 is merged: https://github.com/officialoroe-crypto/sage-one/pull/220. Squash merge commit: `701d48a456a172d7fb0d89fac7a44b6e7fe30014`.
- PR head `f67d31e501920a6469ed7bb0889b5b1bbb98ed6c`; GitHub reported mergeable=true before merge. SAGE CI #1836, public website PR validation #196, and Android Release #357 all completed successfully. The website PR build intentionally skipped deploy because it was a pull_request event.
- The main Pages workflow now requires `vars.SAGE_API_URL` to be nonempty HTTPS on non-PR runs and passes it to Flutter using `--dart-define=SAGE_API_URL=...`. This prevents a public deploy from silently reverting to localhost.
- No real hosted API URL or Actions variable is confirmed in this checkpoint. Backend service is not yet live/verified. Do not run workflow expecting success until the real backend is live, `/health` and `/identity/config` pass, and repository variable `SAGE_API_URL` contains the actual HTTPS base URL without trailing slash.
- Owner steps: GitHub repository Settings → Secrets and variables → Actions → Variables → New repository variable; name `SAGE_API_URL`, value actual tested Render service base URL. Then Actions → SAGE ONE Public Website and Web App → Run workflow on `main`. Confirm both build and deploy jobs succeed, then browser-test `/sage-one/app/` and verify Network has no `localhost:8010` requests.
- Render free tier is test-only for now: service can sleep and filesystem is ephemeral; don't store real user data until durable DB is configured. Keep avoiding local Flutter/Gradle builds due laptop resource constraints.


## Render backend startup error — 2026-10-11
- Owner provided Render log: SQLAlchemy raises `ArgumentError: Could not parse SQLAlchemy URL from given URL string` in `database/connection.py`, then Uvicorn exits status 1. Owner also reports `/health` JSON success/healthy, so verify endpoint again after fixing/redeploying because the healthy response may come from a prior instance or different deployment.
- Inspected `database/connection.py` on main: `SAGE_DATABASE_URL` environment variable overrides fallback `sqlite:///./sage_one.db`; a malformed or empty-but-present value causes this exact error.
- Immediate smoke-test fix: Render service Environment → remove `SAGE_DATABASE_URL` entirely if no DB is configured, allowing SQLite fallback temporarily; or set it to the real PostgreSQL URL copied from the Render DB Connect page. Save and redeploy. Never put DB credentials in chat or public repo.
- SQLite on Render Free is ephemeral and unsuitable for real user data. Configure durable storage before production use. After redeploy, retest `/health` and `/identity/config`; only then configure Actions variable `SAGE_API_URL` and run Pages workflow.


## Render troubleshooting and Pages workflow navigation — 2026-10-11
- Render startup crash: SQLAlchemy cannot parse URL in `database/connection.py`. Verified source reads `SAGE_DATABASE_URL` with SQLite fallback; invalid/empty variable overrides fallback. Remove it only if no database exists for temporary smoke testing, or correct it using the real DB connection URL. Never send credentials in chat. SQLite on Render Free is ephemeral, not for real user data.
- User says repository Actions variable `SAGE_API_URL` has been added, but they cannot find the workflow. Workflow name is `SAGE ONE Public Website and Web App`, filename `.github/workflows/sage-one-god-mode-pages.yml`, direct UI URL https://github.com/officialoroe-crypto/sage-one/actions/workflows/sage-one-god-mode-pages.yml.
- Do not run Pages workflow until backend startup is stable and `/health` + `/identity/config` have been rechecked after redeploy, and `SAGE_API_URL` is the actual HTTPS base URL. Workflow intentionally fails when the variable is missing or non-HTTPS.
- Identity endpoint currently reported `developer_mode:false` and `owner_mode_available:false`; Google client ID field appeared blank/omitted. OAuth/owner login not verified; troubleshoot after service remains healthy.
