# AWS ECS (EC2) deployment

See the full guide: **[iac.md](../iac.md)** (architecture, bootstrap, GitHub Actions, sizing, troubleshooting).

## Separate containers vs single container

**Use separate containers** (recommended and what this stack deploys):

| | Separate containers | Single container |
|---|---|---|
| Scaling | Scale API and voice agent independently | Must scale both together |
| Memory | Voice agent ~4–8 GB; API ~1 GB | One box needs ~10 GB+ always |
| Deploys | Update API without restarting calls | Any API change restarts the agent |
| Security | API behind ALB; agent outbound-only | Larger blast radius |
| Failure | API crash does not kill active calls | Shared process risk |

The voice agent only needs outbound network (LiveKit, STT, TTS, LLM). The API needs inbound HTTP for uploads and health checks. Different roles → different ECS services.

## Architecture

```
Internet (optional) ──► ALB ──► API task (8090)
                              ▲
Voice agent task ─────────────┘  RAG_API_BASE_URL=http://api.<namespace>:8090
     │
     └──► LiveKit Cloud, Deepgram, Cartesia, xAI (outbound)

Qdrant Cloud / RDS — external managed services (not in this Terraform)
```

## Prerequisites

1. **Do not use the AWS root user** for Terraform or GitHub Actions. Create an IAM admin user (or use IAM Identity Center) for bootstrap, then use the GitHub OIDC role for CI/CD.
2. AWS CLI configured for bootstrap (`aws configure` with a non-root IAM user).
3. Terraform >= 1.5.
4. GitHub repository with Actions enabled.
5. Populate secrets in **SSM Parameter Store** after first `terraform apply` (see below).

## Bootstrap (one time)

```powershell
cd infra/terraform

# Copy and edit variables (no secrets in git)
copy terraform.tfvars.example terraform.tfvars

# Remote state (recommended): create S3 bucket (enable versioning), then copy backend.tf.example -> backend.tf
terraform init
terraform plan
terraform apply
```

After apply, set secret values (Console → Systems Manager → Parameter Store, or script):

```powershell
# From api/.env + voice-agent/.env (recommended)
python infra/scripts/sync_ssm_parameters.py --from-local-env --dry-run
python infra/scripts/sync_ssm_parameters.py --from-local-env --region ap-south-1 --profile relaydesk-admin

# Or build infra/scripts/env.properties first, then upload
python infra/scripts/sync_ssm_parameters.py --write-env-properties --from-local-env
python infra/scripts/sync_ssm_parameters.py --region ap-south-1
```

PowerShell:

```powershell
.\infra\scripts\sync-ssm-parameters.ps1 -FromLocalEnv -DryRun
.\infra\scripts\sync-ssm-parameters.ps1 -FromLocalEnv
```

Manual single parameter:

```powershell
aws ssm put-parameter --name "/relaydesk/prod/api/OPENAI_API_KEY" --value "sk-..." --type SecureString --overwrite
```

Build and push initial images (or let GitHub Actions do it on first merge to `main`):

```powershell
$PROFILE_NAME = "relaydesk-admin"
$AWS_REGION   = "ap-south-1"
$ACCOUNT_ID   = terraform output -raw aws_account_id
$ECR_API      = terraform output -raw ecr_api_repository_url
$ECR_VOICE    = terraform output -raw ecr_voice_agent_repository_url
$IMAGE_TAG    = "v1" # or git SHA

aws ecr get-login-password --profile $PROFILE_NAME --region $AWS_REGION |
  docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

cd ../..
docker build -t relaydesk-api:latest ./api
docker build -t relaydesk-voice:latest ./voice-agent

docker tag relaydesk-api:latest "${ECR_API}:${IMAGE_TAG}"
docker tag relaydesk-api:latest "${ECR_API}:latest"
docker push "${ECR_API}:${IMAGE_TAG}"
docker push "${ECR_API}:latest"

docker tag relaydesk-voice:latest "${ECR_VOICE}:${IMAGE_TAG}"
docker tag relaydesk-voice:latest "${ECR_VOICE}:latest"
docker push "${ECR_VOICE}:${IMAGE_TAG}"
docker push "${ECR_VOICE}:latest"
```

## GitHub Actions

1. Add repository variables: `AWS_REGION`, `AWS_ROLE_ARN` (from `terraform output github_actions_role_arn`).
2. Push to `main` (or run workflow manually) — builds both images, pushes to ECR, redeploys ECS services.

## Sizing (default)

| Component | ECS task | EC2 host |
|-----------|----------|----------|
| API | 0.25 vCPU, 512 MiB RAM | `t3.large` (shared) |
| Voice agent | **~1.75 vCPU, 7040 MiB RAM** | Same host as API (fits t3.large with API) |

**Free Tier (API only):** `ecs_instance_type = "t3.micro"` and `voice_agent_desired_count = 0`.

Changing `ecs_instance_type` updates the launch template only — **existing EC2 instances are not replaced automatically**. Run an ASG instance refresh after apply (see `infra/scripts/asg-instance-refresh-prefs.json`). If refresh stalls with *instance is protected*, remove scale-in protection on the old node first:

```powershell
aws autoscaling set-instance-protection `
  --instance-ids <instance-id> `
  --auto-scaling-group-name relaydesk-prod-ecs `
  --no-protected-from-scale-in `
  --region ap-south-1 `
  --profile relaydesk-admin
```

Preferences file for manual refresh: `infra/scripts/asg-instance-refresh-prefs.json`.

```powershell
aws autoscaling start-instance-refresh `
  --auto-scaling-group-name relaydesk-prod-ecs `
  --region ap-south-1 `
  --profile relaydesk-admin `
  --preferences file://c:/Users/Swati/Downloads/telephone-agent/infra/scripts/asg-instance-refresh-prefs.json
```

For production with many concurrent calls, increase `ecs_instance_desired_capacity` and/or run dedicated instance types via a second capacity provider (advanced).

## Live logs (ECS / CloudWatch)

Log groups (from Terraform): `/ecs/relaydesk-prod/api` and `/ecs/relaydesk-prod/voice-agent`.

```powershell
$PROFILE_NAME = "relaydesk-admin"
$AWS_REGION   = "ap-south-1"

# API
aws logs tail /ecs/relaydesk-prod/api --since 10m --follow --region $AWS_REGION --profile $PROFILE_NAME

# Voice agent (separate terminal)
aws logs tail /ecs/relaydesk-prod/voice-agent --since 10m --follow --region $AWS_REGION --profile $PROFILE_NAME
```

Set `$env:AWS_PROFILE = "relaydesk-admin"` instead of `--profile` if you prefer.

## Region

Default: `ap-south-1` (Mumbai). Change `aws_region` in `terraform.tfvars` if needed. Co-locate with LiveKit **India West** and Qdrant/RDS in the same region when possible.

## Cost monitoring (Budget + dashboard)

Terraform creates:

| Resource | Purpose |
|----------|---------|
| **CloudWatch dashboard** `relaydesk-prod-billing` | Month-to-date **estimated** charges (total + by service). Metrics in `us-east-1`, update every few hours. |
| **AWS Budget** `relaydesk-prod-monthly` | Monthly limit for resources tagged `Project=relaydesk`; optional email alerts. |
| **Cost allocation tags** | Activates `Project` and `Environment` tags in Cost Explorer. |

Configure in `terraform.tfvars`:

```hcl
enable_cost_monitoring = true
monthly_budget_usd     = 75
budget_alert_emails    = ["you@example.com"]  # optional
```

After `terraform apply`, open the dashboard:

```powershell
terraform output billing_dashboard_url
terraform output cost_explorer_url
```

**Cost Explorer (recommended for forecast):** Billing → Cost Explorer → set date range **Month-to-date** → **Group by: Service** → add filter **Tag: Project = relaydesk**. The **Forecasted month end** line shows projected monthly cost from current usage.

**Enable billing metrics** (one-time, if the dashboard is empty): Billing → Billing preferences → turn on **Receive Billing Alerts**.

**Note:** New cost allocation tags can take up to **24 hours** before tagged spend appears in Cost Explorer.
