# sage-one-bot

Full backup of the SAGE ONE project (backend, website, phone app, docs, tests, workflows), kept for the owner so it can be run, edited or handed to any AI tool even if a Claude session is lost. This repository is the one Claude works in.

## What is in here

| Folder | What it is |
|---|---|
| `app/`, `identity/`, `permissions/`, `economy/`, `missions/`, `tasks/`, `brain/`, ... | Python backend (FastAPI) |
| `website/` | Static website, web chat app and phone page (plain HTML, CSS, JS) |
| `frontend/` | Flutter phone app |
| `tests/` | Backend tests (259) |
| `docs/`, `*.md` | Blueprint, rules, state, decisions |
| `SECURITY.md` | Security audit and hosting runbook |
| `.github/workflows/` | CI, Android build, website publish |

## Run the website on your computer (no install)

```
cd website
python -m http.server 8080
```
Open http://localhost:8080

## Run the backend

```
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env     # then fill in your keys (see below); never commit .env
python -m uvicorn app.main:app --reload
python -m pytest -q tests
```

Secrets are **not** stored in GitHub. Create `.env` yourself with the names listed in `.env.example`.

## Quick start: paste your key and it runs

1. Windows: double-click `start.bat`. Mac/Linux: run `./start.sh`.
2. First run installs everything and asks for your keys (typing is hidden). Get a free Gemini key at aistudio.google.com/apikey, or a free Groq key at console.groq.com. SAGE tests each key on the spot and tells you if it works.
3. Your browser opens the chat. On your own computer press **Local developer sign-in**.
4. To change keys later: `python scripts/sage_setup.py`. To only check: `python scripts/sage_setup.py --check`.

For a public link anyone can open, follow `docs/DEPLOY_PUBLIC.md` (the same keys go into Render instead of a file).

## The real web app (website/chat and website/mobile)

The website has two real pages that talk to the SAGE server. There are no demo replies or fake logins: every answer, rank, Spark balance, task, memory and project comes from the server.

| Page | What it does |
|---|---|
| `website/chat/` | Sign in, first-time setup, chat with SAGE, history, tasks, memory, projects, Evolution, Spark wallet, learning, marketplace and jobs, settings |
| `website/mobile/` | Phone home: real rank and Spark balance, a SAGE button to type or speak, tasks |

What the server needs before the pages are fully useful (put these in the server environment, never in Git):

| Variable | Why |
|---|---|
| `GOOGLE_CLIENT_ID` | Turns on Google sign-in (create an OAuth Web client in Google Cloud and add the website address as an authorised origin) |
| `SAGE_OWNER_AUTH_SUBJECT` | Your Google account id (`sub`), so only you can sign in |
| `GEMINI_API_KEY` / `GROQ_API_KEY` / `CEREBRAS_API_KEY` | At least one, so SAGE can think. Without any key the chat says so honestly |
| `SAGE_CORS_ORIGINS` | The website address(es), e.g. `https://officialoroe-crypto.github.io` |
| `SAGE_DATABASE_URL` | A durable database (hosted Postgres). Free-tier SQLite is wiped on restart |
| `SAGE_ENV=production` | Turns off docs and developer mode |

The server address the pages use is `apiBase` in `website/site-config.js`. If you change it, also update the `connect-src` in the CSP `<meta>` of `chat/index.html` and `mobile/index.html`, and `website/_headers`.

Local end-to-end test without a paid key: `python scripts/dev_test_llm.py` starts a tiny fake AI server (test text only, never used in production). Run the backend with `SAGE_PREFER_LOCAL=true GROQ_API_KEY=test GROQ_BASE_URL=http://127.0.0.1:11434`, serve `website/`, and set `apiBase` to `http://localhost:8000`.

## Publish the website (free)

Settings > Pages > Source: GitHub Actions. The workflow `pages-website.yml` publishes `website/` on every push to `main`. The address will be `https://officialoroe-crypto.github.io/sage-one-bot/`.

## Handing this to another AI tool

Tell it to read, in order: `PROJECT_STATE.md`, `docs/SAGE_MASTER_BLUEPRINT.md`, `DEVELOPMENT_RULES.md`, `SECURITY.md`. The core rule: SAGE can do nothing without the owner's explicit permission.
