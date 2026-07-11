# One-click local dev: RDS tunnel + API + UI (three new terminal windows).
#
# Usage:
#   $env:RDS_DB_PASSWORD = "YourRdsPassword"
#   .\infra\scripts\dev_local.ps1

param(
    [int]$TunnelWaitSeconds = 6,
    [int]$ApiWaitSeconds = 4
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Scripts = $PSScriptRoot

Write-Host ""
Write-Host "RelayDesk local dev"
Write-Host "=================="
Write-Host ""

if (-not $env:RDS_DB_PASSWORD) {
    Write-Error @"
RDS_DB_PASSWORD is not set.

  `$env:RDS_DB_PASSWORD = "YourRdsPassword"
  .\infra\scripts\dev_local.ps1
"@
}

if (-not (Test-Path (Join-Path $Root "ui\.env"))) {
    Write-Error "ui\.env not found. Copy ui\.env.example to ui\.env first."
}

Write-Host "[1/3] Opening RDS tunnel (localhost:15432)..."
Start-Process cmd -ArgumentList @(
    "/k",
    "cd /d `"$Scripts`" && call rds_tunnel.bat"
) -WindowStyle Normal

Write-Host "      Waiting for tunnel..."
Start-Sleep -Seconds $TunnelWaitSeconds

Write-Host "[2/3] Opening local API (:8090)..."
Start-Process cmd -ArgumentList @(
    "/k",
    "cd /d `"$Root`" && call `"$Scripts\start_local_api.bat`""
) -WindowStyle Normal

Write-Host "      Waiting for API..."
Start-Sleep -Seconds $ApiWaitSeconds

Write-Host "[3/3] Opening local UI (:3000)..."
Start-Process cmd -ArgumentList @(
    "/k",
    "cd /d `"$Root`" && call `"$Scripts\start_local_ui.bat`""
) -WindowStyle Normal

Write-Host ""
Write-Host "Local dev started in separate windows:"
Write-Host "  UI:  http://localhost:3000"
Write-Host "  API: http://127.0.0.1:8090/health"
Write-Host ""
Write-Host "Close the three terminal windows when finished."
Write-Host ""
