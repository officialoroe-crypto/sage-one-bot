"""SAGE ONE setup: paste your keys once, SAGE checks them and everything starts.

    python scripts/sage_setup.py            # asks for keys (typing is hidden), checks them live, saves .env
    python scripts/sage_setup.py --check    # only checks what is already in .env / the environment

Keys are saved only to the local .env file (never committed; .gitignore covers it).
Press Enter to keep a value that is already saved or to skip one you do not have.
"""
from __future__ import annotations

import getpass
import os
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
ENV_FILE = Path(os.getenv("SAGE_ENV_FILE", str(ROOT / ".env")))

# (variable, what it is, secret?)
ASK = [
    ("GEMINI_API_KEY", "Google Gemini key (free at aistudio.google.com/apikey)", True),
    ("GROQ_API_KEY", "Groq key (free at console.groq.com)", True),
    ("CEREBRAS_API_KEY", "Cerebras key (free at cloud.cerebras.ai)", True),
    ("GOOGLE_CLIENT_ID", "Google sign-in Client ID (public, ends with .apps.googleusercontent.com)", False),
    ("SAGE_OWNER_AUTH_SUBJECT", "Your Google account id (leave empty on your own computer)", False),
]


def read_env() -> dict[str, str]:
    values: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def write_env(values: dict[str, str]) -> None:
    lines = ["# Written by scripts/sage_setup.py. Never commit this file."]
    lines += [f"{k}={v}" for k, v in values.items() if v != ""]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        ENV_FILE.chmod(0o600)
    except OSError:
        pass


def check_provider(name: str, key: str) -> tuple[bool, str]:
    """Make one tiny live call so a wrong or expired key is found now, not in the middle of a chat."""
    try:
        if name == "GROQ_API_KEY":
            from groq import Groq
            Groq(api_key=key, timeout=15.0).models.list()
        elif name == "CEREBRAS_API_KEY":
            from cerebras.cloud.sdk import Cerebras
            Cerebras(api_key=key, timeout=15.0).models.list()
        elif name == "GEMINI_API_KEY":
            from openai import OpenAI
            OpenAI(api_key=key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/", timeout=15.0).models.list()
        return True, "key works"
    except Exception as error:  # report any failure plainly
        text = str(error).replace(key, "***")
        return False, text.splitlines()[0][:140]


def report(values: dict[str, str], live: bool = True) -> int:
    env = {**os.environ, **{k: v for k, v in values.items() if v}}
    print("\nSAGE readiness")
    print("-" * 60)
    ai_ok = False
    for var, label, _ in ASK[:3]:
        if not env.get(var):
            print(f"  [ -- ] {var}: not set")
            continue
        if live:
            ok, why = check_provider(var, env[var])
            print(f"  [{'OK' if ok else 'FAIL'}] {var}: {why}")
            ai_ok = ai_ok or ok
        else:
            print(f"  [ set ] {var}")
            ai_ok = True
    google = bool(env.get("GOOGLE_CLIENT_ID"))
    print(f"  [{' OK ' if google else ' -- '}] Google sign-in: " + ("configured" if google else "not set (on your own computer the Local developer sign-in button works instead)"))
    db = env.get("SAGE_DATABASE_URL", "")
    print(f"  [{' OK ' if db.startswith('postgres') else ' -- '}] Database: " + ("Postgres (permanent)" if db.startswith("postgres") else "local file (fine at home; use Postgres when hosted)"))
    print("-" * 60)
    if ai_ok:
        print("SAGE can think. Start it with start.bat (Windows) or ./start.sh (Mac/Linux).")
        return 0
    print("No working AI key yet, so chat will say it has no AI. Add at least one key above and run this again.")
    return 1


def main() -> int:
    values = read_env()
    check_only = "--check" in sys.argv
    if not check_only:
        print(__doc__)
        for var, label, secret in ASK:
            current = values.get(var, "")
            prompt = f"{label}\n  {var}" + (" [saved, Enter to keep]" if current else " (Enter to skip)") + ": "
            entered = (getpass.getpass(prompt) if secret else input(prompt)).strip()
            if entered:
                values[var] = entered
        values.setdefault("SAGE_ENV", "development")
        write_env(values)
        print(f"\nSaved to {ENV_FILE}")
    else:
        for k, v in os.environ.items():
            if k in {a[0] for a in ASK} and k not in values:
                values[k] = v
    return report(values, live=True)


if __name__ == "__main__":
    raise SystemExit(main())
