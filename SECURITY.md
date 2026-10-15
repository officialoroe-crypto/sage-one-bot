# SAGE ONE — Security Report and Hosting Runbook

Audit date: 2026-10-15 (Nepal). Scope: backend (`app/`, `identity/`, `permissions/`, `database/`, `config/`), CI workflows, static website (`website/`), Git history (521 commits).

**Honest limits.** No one can promise "unhackable" or "no mistakes". This report says what was checked, what was fixed, what is still open, and what only the owner can do (accounts, secrets, hosting settings). The checks that were run are repeatable (see the end).

## 1. What was found and what was done

| Area | Finding | Status |
|---|---|---|
| Secrets in code | None in the working tree. Keys are read from environment variables only (`config/settings.py`). | OK |
| Secrets in Git history | Regex scan plus `detect-secrets` over all 521 commits: no keys, tokens or `.env` files. The one hit (`ollama_provider.py`, `api_key="ollama"`) is the public placeholder Ollama expects, not a secret. | OK |
| `.gitignore` | Already covered `.env`, `*.db`, logs. Added `*.pem *.key *.p12 *.jks *.keystore key.properties google-services.json service-account*.json`. No such files are tracked. | Fixed |
| Authentication | Every API route needs a verified Google ID token (checked against Google, audience = your client ID). Control-plane routes also need *owner* identity. | OK |
| Production owner lock | In production only the Google account whose `sub` equals `SAGE_OWNER_AUTH_SUBJECT` can sign in. | OK |
| Dev login / Developer Mode | Localhost-only, but could be switched on by an env var. Now **forced off whenever `SAGE_ENV=production`**; dev sessions also expire after 12 h. | Fixed |
| Passwords | SAGE has **no passwords**: sign-in is Google only, so there is nothing to hash or leak. If passwords are ever added, use argon2/bcrypt, never SHA. | N/A |
| OTP codes | Were stored as plain SHA-256 (a 6-digit code can be brute-forced from a leaked hash) and sends were unlimited (SMS cost abuse). Now keyed HMAC with a per-process secret, max 3 sends per 10 min per user, expired challenges purged. | Fixed |
| Security headers | None were set. Added: CSP, `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, COOP/CORP, `Cache-Control: no-store`, HSTS (production). | Fixed |
| Rate limiting | None. Added per-IP limit (default 120/min) and a strict limit on login/OTP routes (default 10/min), with `Retry-After`. | Fixed |
| Request size | None. Bodies over 1 MB (declared or streamed) get 413. | Fixed |
| Input validation | Several request models had unbounded strings. Added length limits to chat, execute, mission, memory, permission, automation and sales inputs. | Fixed |
| CORS | `allow_methods/headers = *` with credentials. Narrowed to the needed methods/headers and an explicit origin list; production refuses `*` and non-https origins. | Fixed |
| Debug / docs | `/docs`, `/redoc` and `/openapi.json` were public. Disabled in production; `debug=False`. | Fixed |
| Error leakage | `/tools/execute` returned raw exception text; unhandled errors could expose internals. Now a generic message, details go to server logs. | Fixed |
| Google outage | A Google key-endpoint failure caused HTTP 500. Now 503. | Fixed |
| Fail-closed startup | A production start without `GOOGLE_CLIENT_ID` or `SAGE_OWNER_AUTH_SUBJECT`, or with bad CORS, now refuses to boot. | Added |
| Database | Uses SQLAlchemy ORM (parameterised queries; no string-built SQL found by bandit). Added `postgres://` URL fix and `pool_pre_ping`. | OK |
| Dependencies | `pip-audit`: only `pytest 8.4.2` was vulnerable. Moved pytest/ruff to `requirements-dev.txt` (pytest >= 9.0.3); production installs no test tools. CI uses the dev file. Now: no known vulnerabilities. | Fixed |
| Static analysis | `bandit`: 0 medium/high. Lows are `try/except/pass` and the owner-gated `subprocess` in `dev_agent`. | Accepted |
| Website | No XSS found: user text is written with `textContent`, interpolated values are escaped. Added a Content-Security-Policy (meta tag + `website/_headers`), no inline scripts, `no-referrer`. Verified in a real browser: no violations. | Fixed |
| CI workflows | Least-privilege `permissions`, no secrets used. | OK |

Tests: 255 pass, including 12 new ones in `tests/test_security_hardening.py` (headers, body limit, rate limit, spoofed `X-Forwarded-For`, production lockdown, CORS, OTP throttle, dev-session expiry). A live server run confirmed: docs 404, protected routes 401, headers present, 6th login attempt gets 429, evil origin gets no CORS header.

## 2. Still open (needs you or a decision)

1. **The website chat is a demo.** `website/chat` and `app-preview` use scripted replies and a *simulated* sign-in. They are safe to publish because they hold no data and call no API. Connecting them to the real backend (Google sign-in, then `/command`) is the next product step; do it only with the real Google flow.
2. **Free hosting has no durable database.** Render's free filesystem is wiped on redeploy, so SQLite data is lost. For real use, attach a Postgres database (see section 3) and install a driver (`psycopg[binary]`).
3. **GitHub Pages cannot send HTTP headers.** The meta CSP covers scripts and resources, but `frame-ancestors`, HSTS and `X-Frame-Options` need real headers. Put the site behind Cloudflare (free) using `website/_headers`, or host it on Cloudflare Pages / Netlify, which read that file.
4. **Rate limits are per server process, in memory.** Fine for one instance. Use Cloudflare rate-limiting rules as the outer layer.
5. **No audit of the Flutter app's secure storage or Android signing.** Never commit keystores (now git-ignored).
6. **Account security is outside the code.** Turn on 2-step verification (use an authenticator app or passkey) for GitHub, Google, Render and your domain registrar. Use a GitHub fine-grained token with only the repos needed. These protect you more than any code change.

## 3. Hosting runbook (free tier, multi-device)

**Backend on Render (free web service)**

1. Render > New > Web Service > connect `officialoroe-crypto/sage-one`, branch `main`.
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --no-server-header`
4. Environment variables (Render > Environment; **never** put these in Git):

| Variable | Value |
|---|---|
| `SAGE_ENV` | `production` |
| `GOOGLE_CLIENT_ID` | your Google OAuth web client ID |
| `SAGE_OWNER_AUTH_SUBJECT` | your Google account `sub` (see below) |
| `SAGE_CORS_ORIGINS` | `https://officialoroe-crypto.github.io` (your site origin, https only, no trailing path) |
| `SAGE_TRUST_PROXY_HEADERS` | `true` (Render's proxy sets `X-Forwarded-For`; needed so rate limits are per visitor, not global) |
| `SAGE_DATABASE_URL` | Postgres URL from your database provider |
| `GEMINI_API_KEY`, `GROQ_API_KEY`, `CEREBRAS_API_KEY`, `OPENROUTER_API_KEY` | only the providers you use |

5. Do **not** set `SAGE_DEV_MODE` or `SAGE_PRIVATE_MODE` (they are ignored in production anyway).
6. Finding your Google `sub`: sign in once with Google against a *non-production* run (or a local one) and read `identity.subject` in the `/identity/google` response. Then set it in Render.
7. Check: `https://<your-service>.onrender.com/docs` must be 404, `/tasks` must be 401, `/health` must be 200.
8. Free services sleep after inactivity; the first request after sleep is slow. That is normal.

**Database:** a free hosted Postgres (for example Neon or Supabase; check their current free-tier terms) gives you the connection string. Add `psycopg[binary]>=3.1` to `requirements.txt` and use a `postgresql+psycopg://...` URL.

**Website:** keep GitHub Pages for now, or move to Cloudflare Pages to get the real security headers from `website/_headers`. Either way, turn on HTTPS-only.

**Secrets hygiene:** if any key was ever pasted into a chat, screenshot or commit, rotate it at the provider and treat the old one as burned. The Git history scan found none committed.

## 4. Re-running the checks

```
pip install -r requirements-dev.txt bandit detect-secrets pip-audit
python -m pytest -q tests
pip-audit -r requirements.txt
bandit -q -r app identity config permissions database
git log -p --all | grep -nEi "(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}"
```
