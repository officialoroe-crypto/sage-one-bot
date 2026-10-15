# sage-one-bot

Full backup of the SAGE ONE project (backend, website, phone app, docs, tests, workflows), kept for the owner so it can be run, edited or handed to any AI tool even if a Claude session is lost. This repository is the one Claude works in.

## What is in here

| Folder | What it is |
|---|---|
| `app/`, `identity/`, `permissions/`, `economy/`, `missions/`, `tasks/`, `brain/`, ... | Python backend (FastAPI) |
| `website/` | Static website, web chat preview and phone app preview (plain HTML, CSS, JS) |
| `frontend/` | Flutter phone app |
| `tests/` | Backend tests (255) |
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

## Publish the website (free)

Settings > Pages > Source: GitHub Actions. The workflow `pages-website.yml` publishes `website/` on every push to `main`. The address will be `https://officialoroe-crypto.github.io/sage-one-bot/`.

## Handing this to another AI tool

Tell it to read, in order: `PROJECT_STATE.md`, `docs/SAGE_MASTER_BLUEPRINT.md`, `DEVELOPMENT_RULES.md`, `SECURITY.md`. The core rule: SAGE can do nothing without the owner's explicit permission.
