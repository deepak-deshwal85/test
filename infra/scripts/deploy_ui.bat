@echo off
cd /d "%~dp0..\.."
python infra\scripts\deploy_ui.py %*
pause
