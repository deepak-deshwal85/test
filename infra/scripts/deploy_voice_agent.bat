@echo off
cd /d "%~dp0..\.."
python infra\scripts\deploy_voice_agent.py %*
pause
