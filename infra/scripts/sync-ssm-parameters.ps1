# Upload RelayDesk secrets to AWS SSM Parameter Store.
#
# Templates: api/.env.example, voice-agent/.env.example, ui/.env.example
# Sources (default): api/.env + voice-agent/.env + ui/.env
#
#   .\infra\scripts\sync-ssm-parameters.ps1 -DryRun
#   .\infra\scripts\sync-ssm-parameters.ps1
#
# Optional combined file (gitignored):
#   .\infra\scripts\sync-ssm-parameters.ps1 -WriteEnvProperties

param(
    [string]$Region = "ap-south-1",
    [string]$Project = "relaydesk",
    [string]$Environment = "prod",
    [string]$Profile = "",
    [switch]$FromLocalEnv,
    [switch]$WriteEnvProperties,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Script = Join-Path $PSScriptRoot "sync_ssm_parameters.py"

$argsList = @(
    $Script,
    "--region", $Region,
    "--project", $Project,
    "--environment", $Environment
)

if ($Profile) { $argsList += @("--profile", $Profile) }
if ($FromLocalEnv) { $argsList += "--from-local-env" }
if ($WriteEnvProperties) { $argsList += "--write-env-properties" }
if ($DryRun) { $argsList += "--dry-run" }

python @argsList
