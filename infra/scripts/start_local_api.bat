@echo off
REM Start the API locally against AWS RDS (tunnel) and Qdrant Cloud.
REM
REM Prerequisite — leave open in another terminal:
REM   infra\scripts\rds_tunnel.bat
REM
REM Usage:
REM   set RDS_DB_PASSWORD=YourRdsPassword
REM   infra\scripts\start_local_api.bat

setlocal
cd /d "%~dp0..\.."

if "%RDS_DB_PASSWORD%"=="" (
  echo Set RDS_DB_PASSWORD to your RDS master password.
  exit /b 1
)

call infra\scripts\write_local_tunnel_database_url.bat
if errorlevel 1 exit /b 1

cd api
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8090

endlocal
