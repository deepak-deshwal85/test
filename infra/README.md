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

```bash
cd infra/terraform

# Copy and edit variables (no secrets in git)
cp terraform.tfvars.example terraform.tfvars

# Remote state (recommended): create S3 bucket + DynamoDB lock table, then uncomment backend.tf
terraform init
terraform plan
terraform apply
```

After apply, set secret values (Console → Systems Manager → Parameter Store, or CLI):

```bash
aws ssm put-parameter --name "/telephone-agent/prod/api/OPENAI_API_KEY" --value "sk-..." --type SecureString --overwrite
aws ssm put-parameter --name "/telephone-agent/prod/api/DATABASE_URL" --value "postgresql+asyncpg://..." --type SecureString --overwrite
# ... repeat for all parameters listed in terraform output ssm_parameter_names
```

Build and push initial images (or let GitHub Actions do it on first merge to `main`):

```bash
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.ap-south-1.amazonaws.com
docker build -t telephone-agent-api:latest ./api
docker build -t telephone-agent-voice:latest ./voice-agent
# tag and push to ECR URLs from terraform output
```

## GitHub Actions

1. Add repository variables: `AWS_REGION`, `AWS_ROLE_ARN` (from `terraform output github_actions_role_arn`).
2. Push to `main` (or run workflow manually) — builds both images, pushes to ECR, redeploys ECS services.

## Sizing (default)

| Component | ECS task | EC2 instance |
|-----------|----------|--------------|
| Voice agent | 2 vCPU, 8 GB RAM | ASG: `t3.xlarge` (4 vCPU, 16 GB) fits agent + API + overhead |
| API | 0.5 vCPU, 1 GB RAM | Same instance initially; scale ASG for more calls |

For production with many concurrent calls, increase `ecs_instance_desired_capacity` and/or run dedicated instance types via a second capacity provider (advanced).

## Region

Default: `ap-south-1` (Mumbai). Change `aws_region` in `terraform.tfvars` if needed. Co-locate with LiveKit **India West** and Qdrant/RDS in the same region when possible.
