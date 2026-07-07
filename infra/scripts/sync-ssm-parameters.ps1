# Upload RelayDesk secrets from env.properties to AWS SSM Parameter Store.
#
# Quick start (uses api/.env + voice-agent/.env):
#   .\infra\scripts\sync-ssm-parameters.ps1 -FromLocalEnv -DryRun
#   .\infra\scripts\sync-ssm-parameters.ps1 -FromLocalEnv
#
# Or create infra/scripts/env.properties first, then:
#   .\infra\scripts\sync-ssm-parameters.ps1

param(
    [string]$Region = "ap-south-1",
    [string]$Project = "relaydesk",
    [string]$Environment = "prod",
    [switch]$FromLocalEnv,
    [switch]$WriteEnvProperties,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Script = Join-Path $PSScriptRoot "sync_ssm_parameters.py"

$argsList = @(
    $Script,
    "--region", $Region,
    "--project", $Project,
    "--environment", $Environment
)

if ($FromLocalEnv) { $argsList += "--from-local-env" }
if ($WriteEnvProperties) { $argsList += "--write-env-properties" }
if ($DryRun) { $argsList += "--dry-run" }

python @argsList
