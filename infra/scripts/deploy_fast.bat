@echo off
REM Fast single-service deploy (downtime OK). Much quicker than full deploy_all.
REM
REM Examples:
REM   infra\scripts\deploy_fast.bat api
REM   infra\scripts\deploy_fast.bat ui
REM   infra\scripts\deploy_fast.bat voice-agent
REM   infra\scripts\deploy_fast.bat api,ui
REM
REM Fastest iteration during dev: run API/UI locally instead of ECS:
REM   Terminal 1: infra\scripts\rds_tunnel.bat
REM   Terminal 2: infra\scripts\start_local_api.bat
REM   Terminal 3: infra\scripts\start_local_ui.bat

setlocal
cd /d "%~dp0..\.."

if "%~1"=="" (
  echo Usage: deploy_fast.bat ^<api^|ui^|voice-agent^|comma-separated^>
  exit /b 1
)

python infra\scripts\deploy_all.py --fast --only %*
exit /b %errorlevel%
