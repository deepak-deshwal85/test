@echo off
REM Write api/.env.local with DATABASE_URL pointing at AWS RDS.
REM Requires: terraform outputs, RDS password, and (for direct access) rds_publicly_accessible=true.
REM
REM   set RDS_DB_PASSWORD=YourRdsPassword
REM   infra\scripts\set_local_database_url_from_rds.bat

setlocal
cd /d "%~dp0..\.."

if "%RDS_DB_PASSWORD%"=="" (
  echo Set RDS_DB_PASSWORD to your RDS master password.
  exit /b 1
)

python infra\scripts\set_database_url_from_rds.py ^
  --password "%RDS_DB_PASSWORD%" ^
  --write-local-env api\.env.local %*

endlocal
