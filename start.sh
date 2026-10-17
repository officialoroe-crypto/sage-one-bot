#!/usr/bin/env bash
# One command start: ./start.sh   (first run installs everything and asks for your keys)
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
pip install -q -r requirements.txt
[ -f .env ] || python scripts/sage_setup.py || true
python scripts/sage_setup.py --check || true
echo; echo "Starting SAGE: website http://localhost:8080  |  server http://localhost:8000"
python -m uvicorn app.main:app --port 8000 &
SERVER=$!
trap 'kill $SERVER 2>/dev/null' EXIT
sleep 3
(xdg-open http://localhost:8080/chat/ || open http://localhost:8080/chat/) >/dev/null 2>&1 || true
python -m http.server 8080 --directory website
