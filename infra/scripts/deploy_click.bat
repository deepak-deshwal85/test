@echo off
REM Double-click to open the interactive AWS deploy menu.
REM For CLI passthrough: deploy_click.bat --only api

cd /d "%~dp0..\.."
python infra\scripts\deploy_click.py %*
set EXITCODE=%errorlevel%
if %EXITCODE% neq 0 (
  echo.
  echo Deploy failed ^(exit %EXITCODE%^).
  pause
  exit /b %EXITCODE%
)
exit /b 0
