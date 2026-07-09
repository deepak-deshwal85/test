# RelayDesk Infrastructure

AWS infrastructure for RelayDesk: **VPC**, **ECS on EC2**, **ALB**, **Cognito**, **RDS PostgreSQL**, **ECR**, **SSM Parameter Store**, and operational scripts.

[← Back to monorepo](../README.md) · **API deploy:** [`../api/README.md`](../api/README.md) · **UI deploy:** [`../ui/README.md`](../ui/README.md) · **Voice agent deploy:** [`../voice-agent/README.md`](../voice-agent/README.md)

> **Shell:** All commands use **bash** (macOS, Linux, or **Git Bash** on Windows).

---

## Quick reference

| ECS service | Image | Port |
|-------------|-------|------|
| `relaydesk-prod-api` | [`api/Dockerfile`](../api/Dockerfile) | 8090 |
| `relaydesk-prod-ui` | [`ui/Dockerfile`](../ui/Dockerfile) | 3000 |
| `relaydesk-prod-voice-agent` | [`voice-agent/Dockerfile`](../voice-agent/Dockerfile) | — |

Terraform: [`terraform/`](terraform/) · CI/CD: [`.github/workflows/deploy-ecs.yml`](../.github/workflows/deploy-ecs.yml)

**Bootstrap:**

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init && terraform apply
python ../scripts/sync_ssm_parameters.py --profile relaydesk-admin --region ap-south-1
```

**Deploy one service (example — API):**

```bash
export PROFILE_NAME="relaydesk-admin" AWS_REGION="ap-south-1" IMAGE_TAG="latest"
cd infra/terraform
export ECR_API="$(terraform output -raw ecr_api_repository_url)"
cd ../..
docker build -t "${ECR_API}:latest" ./api && docker push "${ECR_API}:latest"
aws ecs update-service --cluster relaydesk-prod --service relaydesk-prod-api \
  --force-new-deployment --profile "$PROFILE_NAME" --region "$AWS_REGION"
```

Sections below cover architecture, secrets, domain setup, Cognito roles, all scripts, and troubleshooting in full.

---

## 1. Overview

### What Terraform provisions

| Resource | Purpose |
|----------|---------|
| **VPC** | Private subnets + NAT gateway for outbound internet |
| **ECS cluster** | `relaydesk-prod` — API, UI, voice-agent services |
| **EC2 Auto Scaling** | Separate ASGs for API (`t3.small`) and voice (`t3.large`) |
| **ALB** | HTTPS termination, routes to UI (`:3000`) and API (`:8090`) |
| **ACM** | TLS certificate for custom domain |
| **Cognito** | User pool, UI client, M2M client, role groups, post-confirmation Lambda |
| **RDS** | PostgreSQL for customers, clients, call jobs |
| **ECR** | Container registries for api, ui, voice-agent |
| **Cloud Map** | `api.relaydesk.local` — internal API DNS for voice agent |
| **SSM** | Secure parameters for all app secrets |
| **CloudWatch** | ECS logs, billing dashboard, monthly budget |
| **IAM** | Task roles, instance profiles, GitHub Actions OIDC role |

### Architecture

```
Internet ──► ALB (HTTPS) ──► UI task (:3000)
                    │
                    ├──► API task (:8090) ──► Qdrant Cloud + RDS
                    │
Voice agent task ───┘  RAG_API_BASE_URL=http://api.relaydesk.local:8090
     │
     └──► LiveKit Cloud, Deepgram, Cartesia, xAI (outbound via NAT)
```

### Why separate containers

| | Separate (deployed) | Single container |
|---|---------------------|------------------|
| Scaling | API and voice scale independently | Both scale together |
| Memory | API ~512 MiB; voice ~8 GiB | One task needs 10+ GiB |
| Deploys | Update API without killing calls | API change restarts agent |
| Security | API behind ALB; agent outbound-only | Larger blast radius |

### Terraform layout

```
infra/
├── README.md                 # This file
├── scripts/                  # Operational Python/shell scripts
└── terraform/
    ├── vpc.tf
    ├── ecs.tf
    ├── alb.tf
    ├── cognito.tf
    ├── cognito_lambda.tf
    ├── rds.tf
    ├── ecr.tf
    ├── ssm.tf
    ├── service_discovery.tf
    ├── iam.tf
    ├── cloudwatch.tf
    ├── variables.tf
    ├── outputs.tf
    └── terraform.tfvars.example
```

---

## 2. Prerequisites

1. **Do not use the AWS root user.** Create an IAM admin user or use IAM Identity Center.
2. AWS CLI configured: `aws configure --profile relaydesk-admin`
3. Terraform >= 1.5
4. Docker (for manual image builds)
5. GitHub repository with Actions enabled (optional CI/CD)

---

## 3. Bootstrap (one-time)

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # edit — no secrets in git

# Optional: remote state
# cp backend.tf.example backend.tf

terraform init
terraform plan
terraform apply
```

### Key `terraform.tfvars` properties

| Variable | Description |
|----------|-------------|
| `aws_region` | Default `ap-south-1` (Mumbai) |
| `project_name` / `environment` | Resource naming prefix |
| `ui_domain_name` | e.g. `relaydesk.uk` — enables ACM + HTTPS |
| `api_ecs_instance_type` | API host, default `t3.small` |
| `voice_ecs_instance_type` | Voice host, default `t3.large` |
| `voice_agent_desired_count` | Set `0` to save cost (Free Tier) |
| `enable_cognito` | Cognito user pool + clients |
| `enable_cognito_google` | Google SSO (requires SSM Google credentials first) |
| `enable_cost_monitoring` | Billing dashboard + budget alerts |
| `monthly_budget_usd` | Budget threshold |
| `api_ecr_image_tag` / `ui_ecr_image_tag` / `voice_ecr_image_tag` | ECS image tags, usually `latest` |

### Useful outputs

```bash
terraform output aws_account_id
terraform output ecs_cluster_name
terraform output ecr_api_repository_url
terraform output ecr_ui_repository_url
terraform output ecr_voice_agent_repository_url
terraform output cognito_user_pool_id
terraform output cognito_callback_urls
terraform output alb_dns_name
terraform output rds_endpoint
terraform output github_actions_role_arn
```

---

## 4. Secrets (SSM Parameter Store)

Terraform creates **placeholder** SSM parameters. Fill them after first apply.

### Sync from local `.env` files

```bash
# Dry run — shows what would be written
python infra/scripts/sync_ssm_parameters.py --dry-run

# Apply (reads api/.env, voice-agent/.env, ui/.env by default)
python infra/scripts/sync_ssm_parameters.py \
  --region ap-south-1 \
  --profile relaydesk-admin

# Also write combined infra/scripts/env.properties (gitignored)
python infra/scripts/sync_ssm_parameters.py --write-env-properties
```

### Set RDS `DATABASE_URL`

If API logs show connection to `127.0.0.1:5432`, sync overwrote with local `.env`:

```bash
export RDS_DB_PASSWORD='your-rds-master-password'

python infra/scripts/set_database_url_from_rds.py \
  --profile relaydesk-admin --region ap-south-1 --dry-run

python infra/scripts/set_database_url_from_rds.py \
  --profile relaydesk-admin --region ap-south-1
```

Then redeploy API:

```bash
aws ecs update-service --cluster relaydesk-prod --service relaydesk-prod-api \
  --force-new-deployment --profile relaydesk-admin --region ap-south-1
```

### Google SSO (optional)

1. `terraform apply` with `enable_cognito_google = false`
2. Add to `infra/scripts/env.properties`:
   ```properties
   GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=GOCSPX-xxxxx
   ```
3. `python infra/scripts/sync_ssm_parameters.py --profile relaydesk-admin --region ap-south-1`
4. Set `enable_cognito_google = true` and `terraform apply`

Google redirect URI: `https://relaydesk-prod.auth.ap-south-1.amazoncognito.com/oauth2/idpresponse`

---

## 5. Build images and deploy ECS

### Manual push (all three services)

From **repo root**:

```bash
export PROFILE_NAME="relaydesk-admin"
export AWS_REGION="ap-south-1"
export IMAGE_TAG="latest"

cd infra/terraform
export ACCOUNT_ID="$(terraform output -raw aws_account_id)"
export ECR_API="$(terraform output -raw ecr_api_repository_url)"
export ECR_UI="$(terraform output -raw ecr_ui_repository_url)"
export ECR_VOICE="$(terraform output -raw ecr_voice_agent_repository_url)"
export CLUSTER="$(terraform output -raw ecs_cluster_name)"
cd ../..

aws ecr get-login-password --profile "$PROFILE_NAME" --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin \
    "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

# Verify each build succeeds before push
docker build -t "${ECR_API}:${IMAGE_TAG}" ./api
docker push "${ECR_API}:${IMAGE_TAG}"
docker push "${ECR_API}:latest"

docker build -t "${ECR_UI}:${IMAGE_TAG}" ./ui
docker push "${ECR_UI}:${IMAGE_TAG}"
docker push "${ECR_UI}:latest"

docker build -t "${ECR_VOICE}:${IMAGE_TAG}" ./voice-agent
docker push "${ECR_VOICE}:${IMAGE_TAG}"
docker push "${ECR_VOICE}:latest"

for SVC in relaydesk-prod-api relaydesk-prod-ui relaydesk-prod-voice-agent; do
  aws ecs update-service --cluster "$CLUSTER" --service "$SVC" \
    --force-new-deployment --profile "$PROFILE_NAME" --region "$AWS_REGION"
done
```

### GitHub Actions (CI/CD)

Workflow: `.github/workflows/deploy-ecs.yml`

1. Set repository variables: `AWS_REGION`, `AWS_ROLE_ARN` (from `terraform output github_actions_role_arn`)
2. Push to `main` — builds, pushes ECR, redeploys ECS

---

## 6. Custom domain (Cloudflare + ACM)

1. Set `ui_domain_name = "relaydesk.uk"` in `terraform.tfvars` and `terraform apply`
2. Add ACM validation CNAME from `terraform output acm_dns_validation_records` (DNS only / gray cloud)
3. Wait for validation, `terraform apply` again
4. Point `@` CNAME to `terraform output -raw alb_dns_name`
5. Cloudflare SSL: **Full (strict)**
6. Verify: `terraform output cognito_production_sso_ready` → `true`
7. Rebuild/push UI so `AUTH_URL` matches production domain

---

## 7. Cognito user roles

| Group | Access |
|-------|--------|
| `guest-clients` | Auto-assigned on SSO sign-up — view-only |
| `approved-clients` | Upload/delete knowledge documents |
| `relaydesk-admins` | Full console and API access |

Voice-agent M2M tokens bypass role checks.

```bash
# Backfill users who signed up before the Lambda existed
python infra/scripts/backfill_guest_clients.py \
  --profile relaydesk-admin --region ap-south-1

# Promote a user
python infra/scripts/approve_cognito_user.py \
  --email user@example.com --role approved-clients \
  --profile relaydesk-admin --region ap-south-1

python infra/scripts/approve_cognito_user.py \
  --email admin@example.com --role relaydesk-admins \
  --profile relaydesk-admin --region ap-south-1

# Revoke elevated roles
python infra/scripts/approve_cognito_user.py \
  --email user@example.com --revoke \
  --profile relaydesk-admin --region ap-south-1
```

Users must **sign out and sign in again** after role changes.

---

## 8. Operational scripts

All scripts in `infra/scripts/`. Run from repo root unless noted.

| Script | Purpose | Example |
|--------|---------|---------|
| **`sync_ssm_parameters.py`** | Push `api/.env`, `voice-agent/.env`, `ui/.env` to SSM | `python infra/scripts/sync_ssm_parameters.py --profile relaydesk-admin --region ap-south-1` |
| **`sync_ssm_parameters.ps1`** | Windows PowerShell variant of SSM sync | `.\infra\scripts\sync-ssm-parameters.ps1` |
| **`set_database_url_from_rds.py`** | Write RDS connection string to SSM `DATABASE_URL` | `python infra/scripts/set_database_url_from_rds.py --profile relaydesk-admin` |
| **`approve_cognito_user.py`** | Assign or revoke Cognito role groups by email | `python infra/scripts/approve_cognito_user.py --email u@x.com --role relaydesk-admins` |
| **`backfill_guest_clients.py`** | Add `guest-clients` group to existing pool users | `python infra/scripts/backfill_guest_clients.py --profile relaydesk-admin` |
| **`sync_cognito_voice_client_secret.py`** | Refresh M2M client secret in SSM from Cognito | `python infra/scripts/sync_cognito_voice_client_secret.py --profile relaydesk-admin` |
| **`cost_control.py`** | Stop/start ECS + ASG (+ optional RDS) to save idle cost | `python infra/scripts/cost_control.py status` · `stop` · `start` |
| **`asg-instance-refresh-prefs.json`** | JSON preferences for ASG instance refresh (not executed directly) | Used with `aws autoscaling start-instance-refresh` |

### `cost_control.py`

```bash
# Current desired counts
python infra/scripts/cost_control.py status \
  --profile relaydesk-admin --region ap-south-1

# Stop ECS tasks and scale ASGs to 0 (saves EC2 compute)
python infra/scripts/cost_control.py stop \
  --profile relaydesk-admin --region ap-south-1

# Also stop RDS (optional)
python infra/scripts/cost_control.py stop \
  --profile relaydesk-admin --region ap-south-1 --include-rds

# Restore from infra/scripts/cost-control-state.json
python infra/scripts/cost_control.py start \
  --profile relaydesk-admin --region ap-south-1 --include-rds
```

**Still billed while stopped:** NAT Gateway, ALB, EIPs, RDS storage, ECR, SSM. Full teardown: `terraform destroy`.

### ASG instance refresh (after changing instance type)

```bash
export PREFS_FILE="file://$(pwd)/infra/scripts/asg-instance-refresh-prefs.json"

aws autoscaling start-instance-refresh \
  --auto-scaling-group-name relaydesk-prod-ecs-api \
  --region ap-south-1 --profile relaydesk-admin \
  --preferences "$PREFS_FILE"

aws autoscaling start-instance-refresh \
  --auto-scaling-group-name relaydesk-prod-ecs-voice \
  --region ap-south-1 --profile relaydesk-admin \
  --preferences "$PREFS_FILE"
```

---

## 9. Monitoring and logs

### CloudWatch log groups

| Service | Log group |
|---------|-----------|
| API | `/ecs/relaydesk-prod/api` |
| Voice agent | `/ecs/relaydesk-prod/voice-agent` |
| UI | `/ecs/relaydesk-prod/ui` |

```bash
export PROFILE_NAME="relaydesk-admin"
export AWS_REGION="ap-south-1"

aws logs tail /ecs/relaydesk-prod/api --since 10m --follow \
  --region "$AWS_REGION" --profile "$PROFILE_NAME"

aws logs tail /ecs/relaydesk-prod/voice-agent --since 10m --follow \
  --region "$AWS_REGION" --profile "$PROFILE_NAME"
```

### Cost monitoring

```bash
terraform output billing_dashboard_url
terraform output cost_explorer_url
```

Enable billing alerts in AWS Console → Billing preferences if the dashboard is empty.

---

## 10. Troubleshooting

| Symptom | Fix |
|---------|-----|
| API connects to `127.0.0.1:5432` | Run `set_database_url_from_rds.py`, redeploy API |
| Voice agent RAG `401` | Run `sync_cognito_voice_client_secret.py`, redeploy voice-agent |
| UI shows old code after push | Verify `docker build` succeeded; force ECS deployment |
| `client_email_id` errors in UI | Redeploy UI + API; sign out/in; complete profile on `/login` |
| Cognito callback mismatch | `terraform output cognito_callback_urls` must match UI `AUTH_URL` |
| Google SSO fails | Check SSM `GOOGLE_*` params and `enable_cognito_google = true` |

### Fix voice-agent M2M secret (Terraform targeted apply)

```bash
cd infra/terraform
terraform apply -target=aws_ssm_parameter.cognito_voice_client_secret[0]
```

---

## 11. Sizing defaults

| Component | ECS task | EC2 host |
|-----------|----------|----------|
| API | 0.25 vCPU, 512 MiB | `t3.small` |
| Voice agent | 2 vCPU, 7680 MiB | `t3.large` |
| UI | 0.25 vCPU, 512 MiB | Shares API ASG |

**Free Tier tip:** `api_ecs_instance_type = "t3.micro"`, `voice_agent_desired_count = 0`.

---

## Related docs

- [`../api/README.md`](../api/README.md) — API local run and scripts
- [`../ui/README.md`](../ui/README.md) — UI local run and Docker
- [`../voice-agent/README.md`](../voice-agent/README.md) — Agent local run and config
