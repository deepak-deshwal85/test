@echo off
REM Write api/.env.local with DATABASE_URL for the RDS SSM tunnel (127.0.0.1:15432).
REM
REM   set RDS_DB_PASSWORD=YourRdsPassword
REM   infra\scripts\write_local_tunnel_database_url.bat
REM   infra\scripts\rds_tunnel.bat

setlocal
cd /d "%~dp0..\.."

if "%RDS_DB_PASSWORD%"=="" (
  echo Set RDS_DB_PASSWORD to your RDS master password.
  exit /b 1
)

python infra\scripts\write_local_tunnel_database_url.py --password "%RDS_DB_PASSWORD%" %*

endlocal
