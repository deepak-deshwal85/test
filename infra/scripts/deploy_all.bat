@echo off
REM Double-click: opens interactive deploy menu (deploy_click.py).
REM Or pass args through to deploy_all.py:
REM   deploy_all.bat --only api
REM   deploy_all.bat --safe
REM
REM Interactive menu only:
REM   infra\scripts\deploy_click.bat

cd /d "%~dp0..\.."
if "%~1"=="" (
  python infra\scripts\deploy_click.py
  exit /b %errorlevel%
)
python infra\scripts\deploy_all.py %*
if errorlevel 1 (
  echo.
  echo Deploy failed. See output above.
  pause
  exit /b 1
)
echo.
echo Deploy finished.
pause
