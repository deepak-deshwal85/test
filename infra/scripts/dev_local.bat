@echo off
REM One-click local dev: RDS tunnel + API + UI (three new terminal windows).
REM
REM Prerequisite — set your RDS password in this terminal first:
REM   set RDS_DB_PASSWORD=YourRdsPassword
REM   infra\scripts\dev_local.bat
REM
REM URLs:
REM   UI:  http://localhost:3000
REM   API: http://127.0.0.1:8090/health

setlocal
cd /d "%~dp0..\.."
set "ROOT=%CD%"
set "SCRIPTS=%~dp0"

echo.
echo RelayDesk local dev
echo ==================
echo.

if "%RDS_DB_PASSWORD%"=="" (
  echo ERROR: RDS_DB_PASSWORD is not set.
  echo.
  echo   set RDS_DB_PASSWORD=YourRdsPassword
  echo   infra\scripts\dev_local.bat
  echo.
  exit /b 1
)

if not exist "%ROOT%\ui\.env" (
  echo ERROR: ui\.env not found. Copy ui\.env.example to ui\.env first.
  exit /b 1
)

echo [1/3] Opening RDS tunnel ^(localhost:15432^)...
start "RelayDesk RDS tunnel" cmd /k "cd /d "%SCRIPTS%" && call rds_tunnel.bat"

echo       Waiting for tunnel...
timeout /t 6 /nobreak >nul

echo [2/3] Opening local API ^(:8090^)...
start "RelayDesk API" cmd /k "cd /d "%ROOT%" && call "%SCRIPTS%start_local_api.bat""

echo       Waiting for API...
timeout /t 4 /nobreak >nul

echo [3/3] Opening local UI ^(:3000^)...
start "RelayDesk UI" cmd /k "cd /d "%ROOT%" && call "%SCRIPTS%start_local_ui.bat""

echo.
echo Local dev started in separate windows:
echo   UI:  http://localhost:3000
echo   API: http://127.0.0.1:8090/health
echo.
echo Close the three terminal windows when finished.
echo.

endlocal
