@echo off
REM Double-click: parallel deploy (api + ui + voice-agent in separate windows).
cd /d "%~dp0..\.."
python infra\scripts\deploy_all.py %*
if errorlevel 1 (
  echo.
  echo Deploy failed. See output above.
  pause
  exit /b 1
)
echo.
echo Deploy finished.
pause
