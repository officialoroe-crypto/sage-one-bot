@echo off
rem One-click start for Windows: double-click start.bat (first run installs everything and asks for your keys)
cd /d "%~dp0"
if not exist .venv ( py -3 -m venv .venv )
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
if not exist .env ( python scripts\sage_setup.py )
python scripts\sage_setup.py --check
echo.
echo Starting SAGE: website http://localhost:8080  /  server http://localhost:8000
start "SAGE server" cmd /k python -m uvicorn app.main:app --port 8000
timeout /t 4 >nul
start "" http://localhost:8080/chat/
python -m http.server 8080 --directory website
