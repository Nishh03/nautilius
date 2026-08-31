@echo off
REM ---------------------------------------------------------------------------
REM Registers FR9-FR11 with Windows Task Scheduler - the free replacement for
REM a paid agent platform. Nothing here needs a subscription.
REM
REM   schedule.bat install     register the three tasks
REM   schedule.bat remove      unregister them
REM   schedule.bat status      show what is registered
REM   schedule.bat test        run all three now, as dry runs
REM
REM Tasks are registered for the current user only, so no admin rights are
REM needed. They run with --apply, so dry-run them yourself first.
REM ---------------------------------------------------------------------------
setlocal
set ROOT=%~dp0..
set PY=python
set ORGANIZE=%ROOT%\automation\organize.py
set DIGEST=%ROOT%\automation\digest.py
set CONFLICTS=%ROOT%\automation\conflicts.py

if "%~1"=="" goto usage
if /i "%~1"=="install"  goto install
if /i "%~1"=="remove"   goto remove
if /i "%~1"=="status"   goto status
if /i "%~1"=="test"     goto test
goto usage

:install
echo Registering Nautilus scheduled tasks...
schtasks /Create /F /TN "Nautilus\Organize"  /SC DAILY  /ST 02:00 ^
  /TR "%PY% \"%ORGANIZE%\" --apply"
schtasks /Create /F /TN "Nautilus\Digest"    /SC WEEKLY /D MON /ST 07:00 ^
  /TR "%PY% \"%DIGEST%\" --apply"
schtasks /Create /F /TN "Nautilus\Conflicts" /SC WEEKLY /D SUN /ST 20:00 ^
  /TR "%PY% \"%CONFLICTS%\" --apply"
echo.
echo Done. FR9 nightly at 02:00, FR10 Mondays at 07:00, FR11 Sundays at 20:00.
echo Every run appends to automation\history.log.
goto end

:remove
schtasks /Delete /F /TN "Nautilus\Organize"
schtasks /Delete /F /TN "Nautilus\Digest"
schtasks /Delete /F /TN "Nautilus\Conflicts"
echo Removed.
goto end

:status
schtasks /Query /TN "Nautilus\Organize"  /FO LIST 2>nul | findstr /C:"TaskName" /C:"Next Run" /C:"Status"
schtasks /Query /TN "Nautilus\Digest"    /FO LIST 2>nul | findstr /C:"TaskName" /C:"Next Run" /C:"Status"
schtasks /Query /TN "Nautilus\Conflicts" /FO LIST 2>nul | findstr /C:"TaskName" /C:"Next Run" /C:"Status"
goto end

:test
echo === FR9 organize (dry run) ===
%PY% "%ORGANIZE%"
echo === FR10 digest (dry run) ===
%PY% "%DIGEST%"
echo === FR11 conflicts (dry run) ===
%PY% "%CONFLICTS%"
goto end

:usage
echo Usage: schedule.bat [install^|remove^|status^|test]

:end
endlocal
