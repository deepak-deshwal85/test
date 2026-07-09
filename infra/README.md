# AWS ECS (EC2) deployment

See the full guide: **[iac.md](../iac.md)** (architecture, bootstrap, GitHub Actions, sizing, troubleshooting).

> **Shell:** Command examples use **bash** (macOS, Linux, or **Git Bash** on Windows).

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

# Remote state (recommended): create S3 bucket (enable versioning), then copy backend.tf.example -> backend.tf
terraform init
terraform plan
terraform apply
```

After apply, set secret values (Console → Systems Manager → Parameter Store, or script):

Copy templates first if needed (`api/.env.example`, `voice-agent/.env.example`, `ui/.env.example`),
fill real values in each app's `.env`, then sync:

```bash
# Reads api/.env + voice-agent/.env + ui/.env by default
python infra/scripts/sync_ssm_parameters.py --dry-run
python infra/scripts/sync_ssm_parameters.py --region ap-south-1 --profile relaydesk-admin

# Optional: also write a combined infra/scripts/env.properties (gitignored)
python infra/scripts/sync_ssm_parameters.py --write-env-properties
```

### Enable Google sign-in (Cognito IdP)

Do **not** put Google client ID/secret in `terraform.tfvars`. Use SSM:

1. `terraform apply` with `enable_cognito_google = false` (creates empty SSM keys under `/relaydesk/prod/cognito/`).
2. Put credentials in `infra/scripts/env.properties` (gitignored):

```properties
GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxx
```

3. Sync:

```bash
python infra/scripts/sync_ssm_parameters.py --region ap-south-1 --profile relaydesk-admin
```

4. Set `enable_cognito_google = true` in `terraform.tfvars` and `terraform apply` again.
   Terraform reads SSM and attaches the Google IdP to Cognito.

Google OAuth redirect URI must be:

```text
https://relaydesk-prod.auth.ap-south-1.amazoncognito.com/oauth2/idpresponse
```

## Custom domain + HTTPS (`relaydesk.uk` via Cloudflare)

CloudFront is **not** used. HTTPS is terminated on the ALB with an **ACM certificate**; DNS stays in **Cloudflare**.

### 1. Terraform

In `terraform.tfvars`:

```hcl
ui_domain_name = "relaydesk.uk"
```

Apply (creates ACM cert + may wait on validation):

```bash
cd infra/terraform
terraform apply
```

### 2. ACM validation in Cloudflare

Get the validation CNAME:

```bash
terraform output acm_dns_validation_records
```

In **Cloudflare → relaydesk.uk → DNS → Add record**:

| Type | Name | Target | Proxy |
|------|------|--------|-------|
| CNAME | `_xxxx.relaydesk.uk` (from output `name`, strip trailing dot) | value from output | **DNS only** (gray cloud) |

Wait 5–15 minutes, then:

```bash
terraform apply
```

Terraform finishes certificate validation and creates the ALB HTTPS listener (`443`).

### 3. Point domain to ALB

```bash
terraform output -raw alb_dns_name
```

Add in Cloudflare:

| Type | Name | Target | Proxy |
|------|------|--------|-------|
| CNAME | `@` (or `relaydesk.uk`) | `relaydesk-prod-api-xxxxx.ap-south-1.elb.amazonaws.com` | DNS only first; then **Full (strict)** SSL |

Cloudflare **SSL/TLS → Overview → Full (strict)** once HTTPS on ALB works.

### 4. Verify Cognito callbacks

```bash
terraform output cognito_callback_urls
terraform output cognito_production_sso_ready   # should be true
```

Should include:

```text
https://relaydesk.uk/api/auth/callback/cognito
```

### 5. Redeploy UI

Rebuild/push UI image and force ECS deployment so `AUTH_URL=https://relaydesk.uk` is picked up:

```bash
# from repo root — see ui/README.md for full ECR commands
export PROFILE_NAME="relaydesk-admin"
export AWS_REGION="ap-south-1"

aws ecs update-service \
  --cluster relaydesk-prod \
  --service relaydesk-prod-ui \
  --force-new-deployment \
  --profile "$PROFILE_NAME" \
  --region "$AWS_REGION"
```

### 6. Test

- Open `https://relaydesk.uk/login`
- Sign in with Cognito (email/password or Google)
- API docs: `https://relaydesk.uk/docs`

**UI parameters:** `AUTH_SECRET`, `COGNITO_CLIENT_SECRET`

### User roles (after SSO sign-in)

New SSO sign-ups get **guest** access automatically (view UI and read data only). An administrator only needs to assign higher roles when required:

| Group | Access |
|-------|--------|
| `guest-clients` | Default for new sign-ups — view UI and read data only |
| `approved-clients` | Guest + upload/delete knowledge-base documents |
| `relaydesk-admins` | Full console and API access |

Voice-agent M2M tokens are exempt from role checks.

1. **Apply Terraform** (creates the three role groups for explicit assignment):

```bash
cd infra/terraform
terraform apply
```

2. **Promote users when needed** (after they have signed in at least once):

```bash
python infra/scripts/approve_cognito_user.py --email user@example.com --role approved-clients
python infra/scripts/approve_cognito_user.py --email your@email.com --role relaydesk-admins
```

3. **Sign out and sign in again** after a role change so the new group appears in the token.

To remove elevated roles (user returns to implicit guest view-only access):

```bash
python infra/scripts/approve_cognito_user.py --email user@example.com --revoke
```

Pool ID is read from `terraform output cognito_user_pool_id` by default.

### Fix API database connection (RDS)

If customer/call-job APIs fail with SQLAlchemy/asyncpg errors connecting to `127.0.0.1:5432`, SSM `DATABASE_URL` still points at **localhost** (often synced from local `api/.env`).

Set it from Terraform RDS outputs:

```bash
# Use the RDS master password from terraform apply (TF_VAR_rds_master_password)
export RDS_DB_PASSWORD='your-rds-password'

python infra/scripts/set_database_url_from_rds.py \
  --profile relaydesk-admin \
  --region ap-south-1 \
  --dry-run

python infra/scripts/set_database_url_from_rds.py \
  --profile relaydesk-admin \
  --region ap-south-1
```

Restart the API ECS task to pick up the new secret:

```bash
aws ecs update-service \
  --cluster relaydesk-prod \
  --service relaydesk-prod-api \
  --force-new-deployment \
  --profile relaydesk-admin \
  --region ap-south-1
```

### Fix voice-agent RAG 401 (Cognito M2M secret drift)

If voice-agent logs show `401 Unauthorized` on `POST /v1/search`, the M2M client secret in SSM may be stale (`invalid_client_secret` at Cognito token endpoint).

Re-sync from Terraform (updates `/relaydesk/prod/voice-agent/COGNITO_CLIENT_SECRET`):

```bash
cd infra/terraform
terraform apply -target=aws_ssm_parameter.cognito_voice_client_secret[0]
```

Then redeploy voice-agent so the task reloads secrets:

```bash
aws ecs update-service \
  --cluster relaydesk-prod \
  --service relaydesk-prod-voice-agent \
  --force-new-deployment \
  --profile relaydesk-admin \
  --region ap-south-1
```

The API auto-creates tables on startup (`bootstrap_database_schema`). `/health` works without DB; customer/call-job routes need a valid RDS URL.

Manual single parameter:

```bash
aws ssm put-parameter --name "/relaydesk/prod/api/OPENAI_API_KEY" --value "sk-..." --type SecureString --overwrite
# Cognito Google IdP:
aws ssm put-parameter --name "/relaydesk/prod/cognito/GOOGLE_CLIENT_ID" --value "..." --type SecureString --overwrite
aws ssm put-parameter --name "/relaydesk/prod/cognito/GOOGLE_CLIENT_SECRET" --value "..." --type SecureString --overwrite
```

Build and push initial images (or let GitHub Actions do it on first merge to `main`). Run from the **repo root** in one shell session (Git Bash). Use `export` so variables survive if you paste commands line by line:

```bash
export PROFILE_NAME="relaydesk-admin"
export AWS_REGION="ap-south-1"
# Must match api_ecr_image_tag / voice_ecr_image_tag in infra/terraform/terraform.tfvars
export IMAGE_TAG="latest"

cd infra/terraform
export ACCOUNT_ID="$(terraform output -raw aws_account_id)"
export ECR_API="$(terraform output -raw ecr_api_repository_url)"
export ECR_VOICE="$(terraform output -raw ecr_voice_agent_repository_url)"
cd ../..

echo "ACCOUNT_ID=$ACCOUNT_ID"
echo "ECR_API=$ECR_API"
echo "ECR_VOICE=$ECR_VOICE"
echo "IMAGE_TAG=$IMAGE_TAG"

aws ecr get-login-password --profile "$PROFILE_NAME" --region "$AWS_REGION" | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

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

**API and voice agent run on separate EC2 instances** (different launch templates / Auto Scaling groups).

| Component | ECS task | Dedicated EC2 host |
|-----------|----------|-------------------|
| API | 0.25 vCPU, 512 MiB RAM | `t3.small` (`api_ecs_instance_type`) |
| Voice agent | 2 vCPU, 7680 MiB RAM | `t3.large` (`voice_ecs_instance_type`) |

Both services stay on the **same ECS cluster** and talk over VPC DNS (`api.relaydesk.local`).

**Free Tier (API only):** `api_ecs_instance_type = "t3.micro"`, `voice_agent_desired_count = 0` (voice ASG scales to 0).

Changing an instance type updates the launch template only — run an **ASG instance refresh** per group after apply (from repo root):

```bash
export PROFILE_NAME="relaydesk-admin"
export AWS_REGION="ap-south-1"
export PREFS_FILE="file://$(pwd)/infra/scripts/asg-instance-refresh-prefs.json"

# API host
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name relaydesk-prod-ecs-api \
  --region "$AWS_REGION" \
  --profile "$PROFILE_NAME" \
  --preferences "$PREFS_FILE"

# Voice host
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name relaydesk-prod-ecs-voice \
  --region "$AWS_REGION" \
  --profile "$PROFILE_NAME" \
  --preferences "$PREFS_FILE"
```

If refresh stalls with *instance is protected*, remove scale-in protection on the old node first:

```bash
aws autoscaling set-instance-protection \
  --instance-ids "<instance-id>" \
  --auto-scaling-group-name relaydesk-prod-ecs \
  --no-protected-from-scale-in \
  --region "$AWS_REGION" \
  --profile "$PROFILE_NAME"
```

Preferences file for manual refresh: `infra/scripts/asg-instance-refresh-prefs.json`.

## Live logs (ECS / CloudWatch)

Log groups (from Terraform): `/ecs/relaydesk-prod/api` and `/ecs/relaydesk-prod/voice-agent`.

```bash
export PROFILE_NAME="relaydesk-admin"
export AWS_REGION="ap-south-1"

# API
aws logs tail /ecs/relaydesk-prod/api --since 10m --follow --region "$AWS_REGION" --profile "$PROFILE_NAME"

# Voice agent (separate terminal)
aws logs tail /ecs/relaydesk-prod/voice-agent --since 10m --follow --region "$AWS_REGION" --profile "$PROFILE_NAME"
```

Or set `export AWS_PROFILE="$PROFILE_NAME"` and omit `--profile` on `aws` commands.

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

```bash
terraform output billing_dashboard_url
terraform output cost_explorer_url
```

**Cost Explorer (recommended for forecast):** Billing → Cost Explorer → set date range **Month-to-date** → **Group by: Service** → add filter **Tag: Project = relaydesk**. The **Forecasted month end** line shows projected monthly cost from current usage.

**Enable billing metrics** (one-time, if the dashboard is empty): Billing → Billing preferences → turn on **Receive Billing Alerts**.

**Note:** New cost allocation tags can take up to **24 hours** before tagged spend appears in Cost Explorer.

### Stop / start resources (save idle cost)

To pause ECS workloads and EC2 hosts overnight or over weekends:

```bash
# See current desired counts
python infra/scripts/cost_control.py status --profile relaydesk-admin --region ap-south-1

# Stop ECS + scale ASGs to 0 (saves EC2/compute). Optionally stop RDS too.
python infra/scripts/cost_control.py stop --profile relaydesk-admin --region ap-south-1 --include-rds

# Restore from infra/scripts/cost-control-state.json
python infra/scripts/cost_control.py start --profile relaydesk-admin --region ap-south-1 --include-rds
```

**Still billed while stopped:** NAT Gateway, ALB, public IPv4 addresses, RDS storage (if RDS stopped), SSM, ECR, etc. Full teardown requires `terraform destroy`.
