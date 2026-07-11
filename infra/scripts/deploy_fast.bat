@echo off
REM Fast single-service AWS deploy (downtime OK). Much quicker than deploying all 3.
REM
REM Examples:
REM   infra\scripts\deploy_fast.bat api
REM   infra\scripts\deploy_fast.bat ui
REM   infra\scripts\deploy_fast.bat voice-agent
REM   infra\scripts\deploy_fast.bat api,ui

setlocal
cd /d "%~dp0..\.."

if "%~1"=="" (
  echo Usage: deploy_fast.bat ^<api^|ui^|voice-agent^|comma-separated^>
  echo.
  echo Example: deploy_fast.bat api
  exit /b 1
)

echo Fast AWS deploy of: %*
python infra\scripts\deploy_all.py --only %*
exit /b %errorlevel%
