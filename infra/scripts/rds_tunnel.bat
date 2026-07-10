@echo off
REM Start RDS SSM tunnel on localhost:15432. Leave this window open.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0rds_tunnel.ps1" %*
