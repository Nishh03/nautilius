@echo off
REM ---------------------------------------------------------------------------
REM Start Nautilus so someone ELSE can open it.
REM
REM   share.bat            serve on this Wi-Fi network (same room)
REM   share.bat tunnel     also create a public link (works from anywhere)
REM
REM Plain run.bat serves only to this machine. This one opens it up, so only
REM run it while you are actually demoing.
REM ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0"

for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /C:"IPv4 Address"') do (
    if not defined LANIP set LANIP=%%A
)
set LANIP=%LANIP: =%

echo.
echo  ============================================================
echo   Nautilus - sharing mode
echo  ============================================================
echo.
echo   On this laptop:      http://127.0.0.1:8000
echo   On the same Wi-Fi:   http://%LANIP%:8000
echo.
if /i "%~1"=="tunnel" (
    echo   A public link will appear below in a few seconds.
    echo   Look for the line ending in .trycloudflare.com
    echo.
    start "Nautilus tunnel" cloudflared tunnel --url http://localhost:8000
)
echo   Keep this window open. Press Ctrl+C to stop sharing.
echo  ============================================================
echo.

python -m uvicorn app:app --app-dir backend --host 0.0.0.0 --port 8000

endlocal
