#!/usr/bin/env bash
# Open a local port that forwards to RDS PostgreSQL through an ECS EC2 host (SSM).
#
# Usage:
#   ./infra/scripts/rds_tunnel.sh
#   LOCAL_PORT=15432 ./infra/scripts/rds_tunnel.sh
#
# Then connect with psql or pgAdmin:
#   Host: localhost
#   Port: 15432
#   Database: relaydesk
#   Username: relaydesk_admin
#   Password: your RDS master password

set -euo pipefail

PROFILE="${PROFILE_NAME:-relaydesk-admin}"
REGION="${AWS_REGION:-ap-south-1}"
LOCAL_PORT="${LOCAL_PORT:-15432}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="${SCRIPT_DIR}/../terraform"

if ! command -v session-manager-plugin >/dev/null 2>&1; then
  echo "Session Manager plugin is required. Install from AWS docs or: winget install Amazon.SessionManagerPlugin" >&2
  exit 1
fi

RDS_HOST="${RDS_HOST:-$(cd "$TERRAFORM_DIR" && terraform output -raw rds_endpoint)}"
INSTANCE_ID="${INSTANCE_ID:-$(aws ec2 describe-instances \
  --profile "$PROFILE" \
  --region "$REGION" \
  --filters "Name=tag:Name,Values=relaydesk-prod-ecs-api" "Name=instance-state-name,Values=running" \
  --query "Reservations[0].Instances[0].InstanceId" \
  --output text)}"

if [[ -z "$INSTANCE_ID" || "$INSTANCE_ID" == "None" ]]; then
  echo "No running relaydesk-prod-ecs-api EC2 instance found." >&2
  exit 1
fi

echo "RDS tunnel"
echo "  local:  localhost:${LOCAL_PORT}"
echo "  remote: ${RDS_HOST}:5432"
echo "  via:    ${INSTANCE_ID} (SSM)"
echo ""
echo "pgAdmin / psql: Host=localhost Port=${LOCAL_PORT} DB=relaydesk User=relaydesk_admin"
echo "Leave this terminal open while connected. Press Ctrl+C to stop."
echo ""

aws ssm start-session \
  --profile "$PROFILE" \
  --region "$REGION" \
  --target "$INSTANCE_ID" \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters "host=${RDS_HOST},portNumber=5432,localPortNumber=${LOCAL_PORT}"
