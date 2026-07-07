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
python infra/scripts/sync_ssm_parameters.py --from-local-env --region ap-south-1

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

| Component | ECS task | EC2 instance |
|-----------|----------|--------------|
| Voice agent | Desired count `0` on Free Tier | Run locally until you scale ECS host |
| API | 0.25 vCPU, 0.5 GB RAM | Runs on `t3.micro` by default |

For production with many concurrent calls, increase `ecs_instance_desired_capacity` and/or run dedicated instance types via a second capacity provider (advanced).

## Region

Default: `ap-south-1` (Mumbai). Change `aws_region` in `terraform.tfvars` if needed. Co-locate with LiveKit **India West** and Qdrant/RDS in the same region when possible.
