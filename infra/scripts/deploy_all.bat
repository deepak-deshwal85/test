@echo off
REM Double-click to build and deploy API, UI, and voice-agent to AWS ECS.
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
