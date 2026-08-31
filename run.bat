@echo off
REM Start Nautilus, then open http://127.0.0.1:8000 in your browser.
cd /d "%~dp0"
python -m uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
