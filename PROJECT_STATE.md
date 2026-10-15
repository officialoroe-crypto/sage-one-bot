# SAGE ONE — PROJECT STATE

Last updated: 2026-10-09
Current main at incident-fix branch creation: 133c5a5f9c8d051e31e9a5d6e7f4aa5e15b99c19

## Identity
- Project: SAGE ONE
- Assistant identity: sage.ai
- Purpose: personal AI mentor and execution partner
- Style: direct, practical, action-oriented, no unnecessary fluff/questions.
- Rules: no lying/hiding important information; permission-based actions.

## Development workflow
- Work in large logical batches.
- GitHub main is the canonical source of truth.
- Use branches/PRs for source changes.
- Use GitHub Actions for heavy validation so the development laptop stays usable.
- Never call a feature complete until success, failure, refresh/restart behavior and regression coverage are checked where practical.
- For work spanning separate AI accounts/sessions, update this file and the relevant task/PR handoff in GitHub; chat memory alone is not synchronization.
- Before resuming, inspect the current main SHA, this file, TODO.md, AI_COLLABORATION.md, coordination/ACTIVE_WORK.yaml, relevant open PRs, and workflow results. Do not rely on older chat summaries when live GitHub state is available.

## Current active handoff — physical Android Google Sign-In

**Status: BLOCKED / device verification pending. Do not mark fixed yet.**

### Observed user-facing error
`Google sign-in exception: code client configuration error. Server client must be provided on Android null`

The user taps “Continue with Google” on the physical Android phone and sees this error. The user also opened the backend `/identity/config` URL in the phone browser and could see the public Google OAuth client ID. That indicates the endpoint was reachable in the browser at that time; it does not prove the installed APK uses that same backend URL or that OAuth is correctly configured end-to-end.

### Environment reported during troubleshooting
- Windows machine: `DESKTOP-ODIMLJ4`; Windows username: `Nishant`.
- Local repo: `C:\\SageOne\\sage_core`; Git Bash path: `/c/SageOne/sage_core`.
- Backend Python environment: `C:\\SageOne\\Backend\\venv\\Scripts\\python.exe`.
- A backend endpoint was previously used at `http://192.168.1.75:8000/chat`.
- Later reported computer LAN IPv4: `192.168.254.3`.
- Config URL tested in phone browser: `http://192.168.254.3:8000/identity/config`.
- The endpoint previously returned `success: true`, a public Google OAuth Web client ID, `developer_mode: true`, and `owner_mode_available: true`.
- ADB path: `/c/Users/Nishant/AppData/Local/Android/Sdk/platform-tools/adb.exe`.
- Previously authorized device ID: `K5J0220415001640`.
- Previous log file: `/c/Users/Nishant/Downloads/sage-google-debug.txt`.
- Recheck the actual current PC IP, backend port/process, device authorization and build URL before relying on these values. This project has used both ports 8000 and 8010.

### Relevant pull requests
- Older PR #190: https://github.com/officialoroe-crypto/sage-one/pull/190
  - Branch: `fix/android-google-signin-client-config`
  - Head SHA: `549edda19a8303ee431eb5fcd4a837dc7d7da7a8`
  - Last inspected state: open, not merged.
- Newer current-main PR #195: https://github.com/officialoroe-crypto/sage-one/pull/195
  - Title: `fix(android): configure Google sign-in client from current main`
  - Branch: `fix/android-google-signin-client-config-current-main`
  - Base SHA: `b1f22d4b074a73f041b4b5db956b6b8848726e26`
  - Head SHA: `9cfdae4b0446af20a3794a46507b794c6a36fe27`
  - Last inspected state: open, not merged, mergeable.
  - This is the newer rebased PR to track; check live PR/CI state before acting. Do not treat PR #190 and #195 as merged or assume either resolves the device issue without a successful device test.
- The proposed code fetches the public Google OAuth Web/server client ID from `/identity/config` on Android when `SAGE_GOOGLE_SERVER_CLIENT_ID` is not supplied at build time. The backend still needs a valid Web application OAuth client ID configured as `GOOGLE_CLIENT_ID` / `settings.GOOGLE_CLIENT_ID`.
- The client must be a public OAuth client ID, never a client secret. Do not place secrets or tokens in this file.

### API URL and release artifact risk
- Flutter's API URL must be reachable from the phone. A physical Android phone's `localhost` points to the phone, not the PC.
- The Android workflow's emulator default `http://10.0.2.2:8010` is not the correct default for a physical phone.
- For the reported LAN setup, `http://192.168.254.3:8000` is a candidate only if the backend is currently listening on port 8000 and the phone can reach it. Verify before building.
- Another documented development route uses ADB reverse with a local API URL, but the port must match the running backend.
- A prior release run #37902855005 and artifact #11603397195 predate the user's later custom-URL run; do not call that artifact the latest custom build.
- The user reported that a later Android workflow completed successfully, but its exact run ID/artifact and embedded API URL were not independently verified at the time of this handoff.

### Exact next actions
1. Inspect PR #195 and its SAGE CI / Android release workflow checks. Prefer this newer current-main PR for the fix; do not merge without required checks and review.
2. Verify current backend port, LAN IP and `/identity/config` response; confirm phone reachability using the exact URL.
3. Open the latest successful Android workflow run and confirm the input `api_url` matches the verified backend URL.
4. Download that run's `sage-one-android-release` artifact, locate the APK within the ZIP instead of assuming its internal folder layout, and install it over USB.
5. Confirm which API URL the installed APK was built with, then retry Google Sign-In.
6. If it still fails, capture fresh Android logs immediately after the attempt and inspect OAuth client type, Android package name/SHA certificate registration, backend configuration, and server-client-ID initialization.
7. Run/inspect SAGE CI and Android release validation for PR #195. Record real results and run IDs here.
8. Only mark resolved after a successful physical-device sign-in and relevant regression checks. Installation or CI success alone is not proof.

### Git Bash commands for artifact installation
Find downloaded artifacts:
```bash
find /c/Users/Nishant/Downloads -maxdepth 1 -type f -iname '*sage-one-android-release*.zip' -printf '%TY-%Tm-%Td %TH:%TM  %p\\n' | sort -r
```

After choosing the ZIP belonging to the latest successful run:
```bash
mkdir -p /c/Users/Nishant/Downloads/sage-one-new-build
unzip -o "/c/Users/Nishant/Downloads/EXACT_ARTIFACT_FILENAME.zip" -d /c/Users/Nishant/Downloads/sage-one-new-build
find /c/Users/Nishant/Downloads/sage-one-new-build -type f -name 'app-release.apk' -print
```

Install the discovered APK:
```bash
APK="$(find /c/Users/Nishant/Downloads/sage-one-new-build -type f -name 'app-release.apk' -print -quit)"
test -n "$APK" || { echo "APK not found; inspect the extracted artifact."; exit 1; }
"/c/Users/Nishant/AppData/Local/Android/Sdk/platform-tools/adb.exe" devices
"/c/Users/Nishant/AppData/Local/Android/Sdk/platform-tools/adb.exe" install -r "$APK"
```

## Current verified product state
Main contains the real private-first execution core:
- Durable worker with atomic claim, ownership leases, heartbeat, retry/backoff and lease recovery.
- Mission planning with dependency-aware bounded execution.
- Real tool execution and verification.
- Research OS with search, web reading, evidence, claims, verification and persistent research records.
- Provider routing with cloud-first controls and protected local fallback.
- Durable notifications and Flutter task polling/filtering.
- Unified Chat `/command` loop with persistent session history and owner/project context.
- Completed durable tasks can index project results and consented experience memory.
- SAGE Voice wake listening, capture and TTS use the same durable command path; Android release validation ensures microphone permission.
- Owner Developer Mode provides non-mutating preview plus explicit approval-gated apply.
- Developer proposals are durable and owner-scoped across API restarts.
- Project detail can queue project-scoped commands.
- Sales Engine is executable end-to-end: discovery → audit → score → durable lead → intelligence → approval-gated outreach → activity history → customer conversion.
- Owner Sales UI exposes lead pipeline, lead detail, approval, customer conversion and human follow-up recording; it never sends external outreach automatically.
- Authenticated identity/profile/onboarding/memory foundations exist.
- Private mobile Memory screen supports profile-scoped read/add/delete and a pending review queue for unconfirmed auto-learned memories, with keep/reject actions.
- World Intelligence has status, knowledge, due items and refresh UI.
- Spark/Evolution foundations are backend-backed and exposed in Flutter.
- Apps Hub/ecosystem surfaces, file manager, AI Studio, wallet, payments, transactions, profile, settings and notifications are exposed from the private shell.
- Final frontend bulk PR #186 is merged. Its exact head passed SAGE CI (214 Python tests; 27 Flutter tests) and Android APK/AAB release validation; the release artifact was uploaded.
- Android release workflow accepts an explicit device backend URL and uses an emulator-reachable host default.
- SAGE CI passes Python compile/lint/tests plus Flutter analyzer/tests.

## Private-first owner mode
- SAGE ONE is currently being built for one owner before public release.
- The private mobile entry path does not require Google sign-in, phone OTP or KYC.
- Developer access is local/owner controlled and production does not inherit private access by default.
- Public signup, multi-tenant ownership, production KYC/SMS and payment-provider expansion remain later scope.

## Safety / authority
- Developer Mode cannot apply source changes without explicit approval.
- God Mode does not create external authority over banks, payments, third-party accounts or destructive external systems.
- Owner economy mutations are audited.
- World Intelligence cannot self-modify production code.

## Economy / Evolution
- Spark is the SAGE platform currency: 1 Spark = NPR 1 (owner decision 2026-10-11; see docs/SAGE_MASTER_BLUEPRINT.md). Cash-out is off until a payment provider is configured and the owner opts in.
- Premium work uses a canonical cost catalogue with reservation → settle/refund lifecycle and owner-scoped idempotency.
- Terminal failure/cancellation refunds exactly once; crash reconciliation exists.
- Verified mission-task results settle lifetime Evolution achievement atomically and idempotently.
- Evolution remains separate from Spark spending.

## Security
- Web Reader validates HTTP/HTTPS targets, blocks private/reserved/link-local targets, validates redirect destinations and bounds content.
- Authentication ownership checks are applied to user/profile/task/project/developer surfaces.
- Developer proposals are owner-scoped by trusted authenticated identity.
- Public worker health does not expose private worker results.

## Validation — historical evidence
- SAGE CI after earlier integration: PASS — run #37886992614.
- God Mode Developer Website after earlier integration: PASS — run #37886992587.
- Android release validation on an earlier exact PR head: PASS; APK/AAB artifact uploaded — run #37886497229.
- Android release validation on an earlier merge commit was reported running at the time — run #37886992592.
- These are historical results; check current workflow runs before using them as evidence for PR #195 or the current physical-device issue.

## Important coordination truth
Several older feature branches and open PRs still exist. Their existence does not mean their work is absent from main. Current main must be treated as the canonical implementation; stale branches should be reconciled or closed only after their changes are compared with main.

## Real remaining blockers
1. Production SMS/OTP provider credentials and delivery.
2. Long-lived Google web token/session refresh UX.
3. Smoke-test the premium lifecycle against the user's configured local database/provider setup.
4. Broader analytics-driven feedback improvement loop.
5. Full multi-tenant isolation only if SAGE becomes a shared public service.
6. Pixel-level visual regression for Evolution animation milestones (existing tests verify the 13-stage catalog, intensity behavior, safe fallback and transition identity, but are not screenshot goldens).
7. Broader external integrations and production release hardening.
8. Manual device/reference review of the complete Flutter surface; CI cannot prove visual fidelity.
9. Physical Android smoke test against the actual configured backend; current Google Sign-In error is documented above.

## Continuity rule
Always inspect actual GitHub main and this file before architectural changes. Do not rely on stale branches or old chat state.

## Multi-AI development coordination
- GitHub main is the synchronization source of truth.
- `AI_COLLABORATION.md` defines claims, path locks, handoffs, reconciliation and branch/PR rules.
- `coordination/ACTIVE_WORK.yaml` is the machine-readable active claim registry; it was empty when last inspected.
- The repository already has a shared AI collaboration/control-plane system, including work claims, handoff contracts, overlap/stale-claim controls, and CI coordination enforcement. Continue using and extending this system rather than creating a parallel handoff process.
- The repository's durable execution core and unified Chat `/command` loop are implemented as listed above; do not restart them just to document this incident.
- Do not silently overwrite another active agent's work.


## Google Sign-In incident — deeper code audit (2026-10-09)

### Confirmed findings
- The current `main` version of `frontend/lib/core/identity_client.dart` only fetches `/identity/config` inside `if (kIsWeb)`. On Android, when `SAGE_GOOGLE_SERVER_CLIENT_ID` is empty, `serverClientId` stays null and is passed to `GoogleSignIn.instance.initialize(...)`. This is a direct front-end defect consistent with the exact reported `serverClientId must be provided on Android` error.
- PR #195 contains the intended Android fallback: when the build-time server client ID is missing, it fetches `google_client_id` from the backend config and passes it as `serverClientId`. PR #195 is open, not merged, at head `9cfdae4b0446af20a3794a46507b794c6a36fe27`.
- The PR #195 Android Release workflow run #37908001368 passed Flutter analysis, Flutter tests, APK build, AAB build and artifact upload. Artifact ID: `11605936415`. This proves the branch builds; it does not prove Google sign-in succeeds on the user's physical phone.
- PR #195 CI checks for the current head were successful, but an earlier Android workflow run #37907727946 failed at Flutter analysis on an earlier merge-ref attempt. Do not confuse that older failed run with the later successful run #37908001368.
- A manual Android Release run #37908676882 on older branch `fix/android-google-signin-client-config` succeeded and uploaded artifact `11605183841`. Its code includes the backend-config fallback, but its `IdentityClient` base URL default is `http://localhost:8010`; that default is not suitable for a physical phone unless an appropriate ADB reverse is configured. The exact `api_url` input used for the user's tested APK has not been independently verified.
- Backend `identity/api.py` exposes `GET /identity/config` with `google_client_id: settings.GOOGLE_CLIENT_ID`. Backend `identity/auth.py` verifies the submitted Google ID token against `settings.GOOGLE_CLIENT_ID`. `config/settings.py` loads that value from environment `GOOGLE_CLIENT_ID`. The user reported that their phone browser could see a client ID at the config URL, which is positive evidence for that endpoint at that time, but not proof the installed APK is using that exact URL/config.
- The error happens during Google Sign-In initialization, before the app submits an ID token to `POST /identity/google`. Therefore the immediate error is in Android client initialization/configuration or the installed APK/build/runtime path, not the backend's ID-token verification handler. Backend audience configuration can still become a second issue after this initialization error is fixed.
- The official Flutter `google_sign_in_android` documentation confirms that when not using Firebase `google-services.json`, the Web application OAuth client ID must be supplied as `serverClientId`. It also lists missing/incorrect server client ID, package name and signing SHA as common configuration issues.

### Most likely reasons the same error persisted
1. The phone still has an APK built from `main` or another artifact that does not contain the fallback.
2. The APK was built from the fixed branch but the user installed a different/older ZIP or APK.
3. The installed APK uses a different `SAGE_API_URL` than the endpoint the user checked in the phone browser.
4. The fixed APK reaches a config endpoint returning no `google_client_id`; the current PR code should report a clearer backend configuration error in this case, so the exact original plugin error would make stale/wrong APK or another initialization path especially important to check.
5. After the immediate error is removed, Google Cloud Android OAuth package name/signing SHA or backend token audience may still require validation.

### Required next verification — do not guess
1. Do not tell the user to keep repeating the same workflow without identifying the artifact. Ask them to install specifically artifact `11605936415` from run #37908001368, or use a new manually dispatched build of PR #195 with the verified physical-device API URL.
2. Verify current backend URL/port from the machine running the server. If using the previously reported LAN endpoint, confirm `http://192.168.254.3:8000/identity/config` is still correct and reachable from the phone. Do not assume the IP/port is unchanged.
3. Confirm the exact `api_url` passed to the build. The workflow's physical-device-safe configuration must match the live backend. Its default `http://127.0.0.1:8010` requires ADB reverse and a backend on port 8010; it does not directly reach a PC's LAN address from the phone.
4. Install the chosen APK using ADB and verify the install command output and device package before testing. Remove old ambiguity by checking the ZIP's timestamp and APK path.
5. Re-test Google sign-in. If the same error persists on the verified PR #195 APK, capture fresh Android logs and add temporary safe diagnostic logging for which configuration branch is selected and whether a non-empty public client ID was retrieved. Never log tokens or secrets.
6. If the Google account selection completes but the backend rejects the ID token, then diagnose `GOOGLE_CLIENT_ID` audience, Android package name and SHA-1/SHA-256 signing fingerprints against Google Cloud OAuth configuration.
7. Keep PR #195 unmerged until current CI and physical-device validation requirements are satisfied. Do not claim fixed until sign-in succeeds on the phone.

### Audit scope and limitation
This was a targeted audit of the authentication client, login screen, auth gate, backend identity config/token-verification paths, settings, Android build workflow, frontend README, identity API tests, Android workflow tests, PR #195 diff and available workflow runs. It was not a literal line-by-line audit of every unrelated repository file or access to the user's current phone runtime.


## Google Sign-In incident — implementation update (2026-10-09)

- Confirmed the defect still existed on main at branch creation: `initializeGoogle()` fetched `/identity/config` only for web, so Android could pass a null `serverClientId` to the Google Sign-In plugin.
- Fix branch: `fix/android-google-signin-runtime-config-20261009`.
- Pull request: https://github.com/officialoroe-crypto/sage-one/pull/196
- Initial fix commit: `3764fcfcbda065ad68accf3b4cd60f8d04bc39ef`; follow-up lint fix: `7bd448e722ab6986954b92317d15ed8988961bd2`.
- Code now loads `google_client_id` from `/identity/config` on Android when the build-time `SAGE_GOOGLE_SERVER_CLIENT_ID` is absent; rejects missing/blank IDs before plugin initialization; and bounds configuration fetch to 12 seconds with an actionable reachability error.
- This is a source-code fix proposal, not yet integrated into main. PR #196 is open and must pass current SAGE CI and Android release validation.
- Device-specific release requirement: build the APK with the backend URL reachable from the physical phone. The previously reported candidate `http://192.168.254.3:8000` must be re-verified at build time; emulator defaults such as `10.0.2.2` and loopback URLs are not valid phone LAN URLs.
- Backend prerequisite: `GOOGLE_CLIENT_ID` must be the Google Cloud **Web application** OAuth client ID. It is a public client ID, not a client secret.
- Regression acceptance: install the exact artifact from the validated run, tap Continue with Google, confirm the Android plugin no longer emits `Server client must be provided on Android null`, and complete the backend token exchange. If OAuth then fails at token verification, investigate package/signing SHA and audience separately.
- Status remains **OPEN / NOT DEVICE-VERIFIED**. Never claim this incident fixed until the exact installed APK completes a physical-device sign-in.


### Follow-up CI failure and correction (2026-10-09)

- PR #196 CI run `37911205477` and Android release run `37911205435` failed Flutter analysis at `identity_client.dart:84:24`: analyzer reported an unnecessary null comparison after flow promotion.
- Removed only the redundant `serverClientId == null` term; retained the non-empty/blank guard before Google plugin initialization. Follow-up commit: `7bd448e722ab6986954b92317d15ed8988961bd2`.
- Follow-up checks for corrected head f06eca91487a3bef24b2bb4cc9ba3b9cd2a028ab passed: SAGE CI run 37911444875 (Python + Flutter) and Android release run 37911444896 (analyze, tests, APK, AAB, artifact upload). The earlier failures remain historical and were corrected.


### Latest launch-readiness check (2026-10-09)

- PR #196 current head at check: f06eca91487a3bef24b2bb4cc9ba3b9cd2a028ab; PR remains open and unmerged.
- SAGE CI run #37911444875: PASS (Python and Flutter jobs).
- Android release run #37911444896: PASS; analyzer, Flutter tests, release APK build, AAB build, and artifact upload all passed.
- Artifact #11607570229 was uploaded from that successful Android release run. Its build log explicitly records SAGE_ANDROID_API_URL=http://127.0.0.1:8010; this loopback URL is not suitable for a normal physical phone unless an intentional ADB reverse setup is configured. Do not hand this artifact to the user as a phone-ready build without fixing/revalidating the API URL.
- Therefore source/CI/release compilation is green, but Google Sign-In remains NOT VERIFIED on a physical device and the current release artifact is not confirmed usable on the user's phone. Before a device build, verify backend host/port and /identity/config, then dispatch Android Release with the phone-reachable URL (candidate only: http://192.168.254.3:8000, must be rechecked). Install that exact artifact and test end-to-end sign-in.
- Public launch remains NO-GO until device auth, full critical-path QA, production backend/deployment, secrets and OAuth configuration, privacy/security review, monitoring/backups, store signing/listing/compliance, and payment/KYC legal/provider requirements applicable to the released scope are addressed.
