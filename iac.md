# Infrastructure as Code (IaC) — AWS ECS on EC2

This document describes how to deploy the **telephone-agent** monorepo on AWS using Terraform and GitHub Actions.

| Project | ECS service | Purpose |
|---------|-------------|---------|
| `voice-agent/` | `telephone-agent-prod-voice-agent` | LiveKit voice agent (STT, LLM, TTS, RAG client) |
| `api/` | `telephone-agent-prod-api` | FastAPI RAG API (Qdrant, embeddings, search) |

Terraform lives in [`infra/terraform/`](infra/terraform/). CI/CD is [`.github/workflows/deploy-ecs.yml`](.github/workflows/deploy-ecs.yml).

---

## Separate containers vs single container

**Use separate containers** (recommended and what this stack deploys).

| | Separate containers | Single container |
|---|---|---|
| **Scaling** | Scale API and voice agent independently | Must scale both together |
| **Memory** | Voice agent ~8 GB; API ~1 GB | One task needs ~10 GB+ always |
| **Deploys** | Update API without restarting active calls | Any API change restarts the agent |
| **Security** | API behind ALB; agent outbound-only | Larger blast radius |
| **Failures** | API crash does not kill active calls | Shared process risk |

The voice agent only needs **outbound** network (LiveKit, Deepgram, Cartesia, xAI). The API needs **inbound** HTTP for uploads and health checks. Different roles → different ECS services.

---

## Architecture

```
Internet (optional) ──► ALB ──► API task :8090
                              ▲
Voice agent task ─────────────┘  RAG_API_BASE_URL=http://api.telephone-agent.local:8090
     │
     └──► LiveKit Cloud, Deepgram, Cartesia, xAI (outbound)

Qdrant Cloud + RDS PostgreSQL — external (configured via SSM secrets, not in Terraform)
```

**Networking**

- ECS tasks run in **private subnets** with a **NAT gateway** for outbound internet (LiveKit, OpenAI, Qdrant Cloud).
- API is registered in **AWS Cloud Map** as `api.telephone-agent.local` so the voice agent resolves it without hard-coding IPs.
- ALB is **internal** by default; set `api_publicly_accessible = true` in Terraform for a public document-upload endpoint.

---

## Repository layout

```
infra/
├── README.md
└── terraform/
    ├── vpc.tf                   # VPC, subnets, NAT, routing
    ├── ecs.tf                   # ECS cluster, EC2 ASG, task defs, services
    ├── alb.tf                   # Application Load Balancer for API
    ├── service_discovery.tf     # Cloud Map: api.telephone-agent.local
    ├── ecr.tf                   # ECR repositories
    ├── iam.tf                   # Task roles, EC2 instance role, GitHub OIDC
    ├── ssm.tf                   # SSM Parameter Store placeholders for secrets
    ├── security_groups.tf
    ├── cloudwatch.tf
    ├── variables.tf
    ├── outputs.tf
    └── terraform.tfvars.example

.github/workflows/deploy-ecs.yml  # Build, push ECR, deploy ECS (OIDC, no access keys)

voice-agent/Dockerfile            # LiveKit agent (uv run src/agent.py start)
api/Dockerfile                    # FastAPI (uvicorn on :8090)
```

---

## Prerequisites

1. **Do not use the AWS root user** for Terraform or GitHub Actions. Create an IAM admin user (or IAM Identity Center) for bootstrap; CI/CD uses the GitHub OIDC role from Terraform output.
2. [AWS CLI](https://aws.amazon.com/cli/) configured with a non-root IAM user.
3. [Terraform](https://www.terraform.io/) >= 1.5.
4. GitHub repository with Actions enabled.
5. External services ready: **LiveKit Cloud**, **Qdrant Cloud** (or self-hosted Qdrant), **RDS PostgreSQL**, API keys (OpenAI, Deepgram, Cartesia, xAI, etc.).

---

## Bootstrap (one time)

### 1. Terraform

```bash
cd infra/terraform

cp terraform.tfvars.example terraform.tfvars
# Edit: github_org, aws_region (default ap-south-1), sizing if needed

# Optional: remote state — see backend.tf.example (S3 + DynamoDB lock)

terraform init
terraform plan
terraform apply
```

Note useful outputs:

```bash
terraform output github_actions_role_arn
terraform output ecr_api_repository_url
terraform output ecr_voice_agent_repository_url
terraform output ssm_api_parameter_names
terraform output ssm_voice_agent_parameter_names
terraform output voice_agent_rag_api_base_url
```

### 2. Set secrets in SSM Parameter Store

Terraform creates placeholder `SecureString` parameters. Set real values after apply (values are **not** stored in Terraform state after you change them):

```bash
aws ssm put-parameter \
  --name "/telephone-agent/prod/api/OPENAI_API_KEY" \
  --value "sk-..." \
  --type SecureString \
  --overwrite

aws ssm put-parameter \
  --name "/telephone-agent/prod/api/DATABASE_URL" \
  --value "postgresql+asyncpg://user:pass@host:5432/telephone_agent" \
  --type SecureString \
  --overwrite

# Repeat for all parameters from:
#   terraform output ssm_api_parameter_names
#   terraform output ssm_voice_agent_parameter_names
```

**API parameters:** `OPENAI_API_KEY`, `DATABASE_URL`, `RAG_API_KEY`, `QDRANT_API_KEY`, `QDRANT_CLUSTER_ENDPOINT`, `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LIVEKIT_SIP_OUTBOUND_TRUNK_ID`

**Voice agent parameters:** `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `XAI_API_KEY`, `DEEPGRAM_API_KEY`, `CARTESIA_API_KEY`, `CALCOM_API_KEY`, `RAG_API_KEY`

### 3. Initial container images (optional)

GitHub Actions can do this on first push to `main`. To push manually:

```bash
AWS_REGION=ap-south-1
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_API=$(terraform output -raw ecr_api_repository_url)
ECR_VOICE=$(terraform output -raw ecr_voice_agent_repository_url)

aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

docker build -t $ECR_API:latest ./api
docker push $ECR_API:latest

docker build -t $ECR_VOICE:latest ./voice-agent
docker push $ECR_VOICE:latest

aws ecs update-service --cluster telephone-agent-prod --service telephone-agent-prod-api --force-new-deployment
aws ecs update-service --cluster telephone-agent-prod --service telephone-agent-prod-voice-agent --force-new-deployment
```

### 4. GitHub repository variables

In **Settings → Secrets and variables → Actions → Variables**:

| Variable | Example value |
|----------|----------------|
| `AWS_ROLE_ARN` | From `terraform output github_actions_role_arn` |
| `AWS_REGION` | `ap-south-1` |
| `ECS_CLUSTER` | `telephone-agent-prod` |
| `ECS_SERVICE_API` | `telephone-agent-prod-api` |
| `ECS_SERVICE_VOICE` | `telephone-agent-prod-voice-agent` |
| `ECR_API_REPO` | `telephone-agent-api` |
| `ECR_VOICE_REPO` | `telephone-agent-voice-agent` |

The workflow **Deploy to ECS (EC2)** runs only when `AWS_ROLE_ARN` is set.

### 5. Deploy via CI/CD

Push to `main` (paths under `api/`, `voice-agent/`, `infra/`) or run the workflow manually. It will:

1. Assume AWS role via **OIDC** (no long-lived access keys).
2. Build and push both Docker images to ECR (tagged with git SHA and `latest`).
3. Register new ECS task definitions and update both services.
4. Wait until services are stable.

---

## Default sizing

| Resource | Default | Notes |
|----------|---------|--------|
| EC2 instance (ECS host) | `t3.xlarge` (4 vCPU, 16 GB) | Fits voice agent + API + ECS agent on one node |
| Voice agent task | 2 vCPU, 8 GB RAM | Turn detector inference needs ~2–3 GB |
| API task | 0.5 vCPU, 1 GB RAM | I/O-bound FastAPI |
| ASG | min 1, max 3, desired 1 | Increase for more concurrent calls |
| NAT gateway | Always on | Required for outbound to LiveKit, OpenAI, Qdrant |

Override in `terraform.tfvars`: `ecs_instance_type`, `voice_agent_cpu`, `voice_agent_memory`, `api_cpu`, `api_memory`, `ecs_instance_desired_capacity`.

---

## Region and latency

- **Default region:** `ap-south-1` (Mumbai).
- **LiveKit Cloud:** India West for callers in India.
- **ECS + RDS + Qdrant:** Same region as the agent when possible to minimize RAG RTT.

Change `aws_region` in `terraform.tfvars`.

---

## Optional: public API

For Swagger / document uploads from the public internet:

```hcl
# terraform.tfvars
api_publicly_accessible = true
```

Then `terraform apply` and use:

```bash
terraform output api_alb_dns_name
# http://<alb-dns>/docs
```

---

## Approximate monthly cost (ap-south-1)

| Service | Estimate |
|---------|----------|
| `t3.xlarge` EC2 (1 node) | ~$120 |
| NAT gateway | ~$32 + data transfer |
| ALB | ~$20 |
| ECR / CloudWatch | ~$5–15 |
| **Subtotal (compute only)** | **~$180–200** |
| RDS, Qdrant Cloud, LiveKit, STT/TTS/LLM APIs | Billed separately |

---

## Security best practices

- Never commit `.env` files or put secrets in `terraform.tfvars`.
- Use SSM SecureString for all API keys and database URLs.
- GitHub Actions uses OIDC with branch-scoped trust (`refs/heads/main`).
- Voice agent has no inbound ports; only the API ALB accepts HTTP.
- Enable S3 remote state + DynamoDB locking for team use (`backend.tf.example`).

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| ECS tasks not starting | EC2 instance joined cluster? ASG healthy? Enough CPU/RAM on instance? |
| `CannotPullContainerError` | Image pushed to ECR? Task execution role has ECR pull? |
| Voice agent can't reach API | Cloud Map DNS `api.telephone-agent.local`? Security group allows 8090 within VPC? |
| API can't reach Qdrant/OpenAI | NAT gateway route on private subnets? SSM secrets set (not `CHANGEME`)? |
| GitHub Action skipped | `AWS_ROLE_ARN` repository variable set? |
| OIDC assume role failed | `github_org` / `github_repo` in tfvars match repository? Branch is `main`? |

**Logs**

```bash
aws logs tail /ecs/telephone-agent-prod/api --follow
aws logs tail /ecs/telephone-agent-prod/voice-agent --follow
```

**SSM into ECS host (debugging)**

```bash
aws ssm start-session --target <ec2-instance-id>
```

---

## Related docs

- [README.md](README.md) — local development
- [infra/README.md](infra/README.md) — short Terraform pointer
- [api/README.md](api/README.md) — RAG API
- [voice-agent/README.md](voice-agent/README.md) — LiveKit agent
