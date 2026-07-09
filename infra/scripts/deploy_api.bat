@echo off
cd /d "%~dp0..\.."
python infra\scripts\deploy_api.py %*
pause
