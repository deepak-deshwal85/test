@echo off
REM Start the UI locally (proxies to local API on :8090).
REM
REM Usage:
REM   infra\scripts\start_local_ui.bat

setlocal
cd /d "%~dp0..\..\ui"

if not exist .env (
  echo Copy ui\.env.example to ui\.env and set AUTH_DISABLE_SSO=true for local dev.
  exit /b 1
)

call npm install
call npm run dev

endlocal
