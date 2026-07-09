# Open a local port that forwards to RDS PostgreSQL through an ECS EC2 host (SSM).
# Requires: AWS CLI, Session Manager plugin, profile relaydesk-admin (or set $env:PROFILE_NAME).
#
# Usage:
#   .\infra\scripts\rds_tunnel.ps1
#   .\infra\scripts\rds_tunnel.ps1 -LocalPort 15432
#
# Then connect with psql or pgAdmin:
#   Host: localhost
#   Port: 15432 (or your -LocalPort)
#   Database: relaydesk
#   Username: relaydesk_admin
#   Password: your RDS master password (TF_VAR_rds_master_password)

param(
    [string]$Profile = $(if ($env:PROFILE_NAME) { $env:PROFILE_NAME } else { "relaydesk-admin" }),
    [string]$Region = $(if ($env:AWS_REGION) { $env:AWS_REGION } else { "ap-south-1" }),
    [int]$LocalPort = 15432,
    [string]$InstanceId = "",
    [string]$RdsHost = ""
)

$ErrorActionPreference = "Stop"

$pluginDir = "C:\Program Files\Amazon\SessionManagerPlugin\bin"
if (Test-Path $pluginDir) {
    $env:Path = "$pluginDir;$env:Path"
}

if (-not (Get-Command session-manager-plugin -ErrorAction SilentlyContinue)) {
    Write-Error @"
Session Manager plugin is required. Install with:
  winget install Amazon.SessionManagerPlugin
Then restart your terminal.
"@
}

$terraformDir = Join-Path $PSScriptRoot "..\terraform"
if (-not $RdsHost) {
    Push-Location $terraformDir
    try {
        $RdsHost = terraform output -raw rds_endpoint
    } finally {
        Pop-Location
    }
}

if (-not $InstanceId) {
    $InstanceId = aws ec2 describe-instances `
        --profile $Profile `
        --region $Region `
        --filters "Name=tag:Name,Values=relaydesk-prod-ecs-api" "Name=instance-state-name,Values=running" `
        --query "Reservations[0].Instances[0].InstanceId" `
        --output text
}

if (-not $InstanceId -or $InstanceId -eq "None") {
    Write-Error "No running relaydesk-prod-ecs-api EC2 instance found. Start the ECS API ASG first."
}

Write-Host "RDS tunnel"
Write-Host "  local:  localhost:$LocalPort"
Write-Host "  remote: ${RdsHost}:5432"
Write-Host "  via:    $InstanceId (SSM)"
Write-Host ""
Write-Host "pgAdmin / psql: Host=localhost Port=$LocalPort DB=relaydesk User=relaydesk_admin"
Write-Host "Leave this window open while connected. Press Ctrl+C to stop."
Write-Host ""

aws ssm start-session `
    --profile $Profile `
    --region $Region `
    --target $InstanceId `
    --document-name AWS-StartPortForwardingSessionToRemoteHost `
    --parameters "host=$RdsHost,portNumber=5432,localPortNumber=$LocalPort"
