# New AWS account — full infrastructure setup

Step-by-step guide to provision RelayDesk in a **fresh AWS account** and get the application running end-to-end.

Use this when you:

- Move to a new AWS account or organization
- Rebuild production from scratch after `terraform destroy`
- Onboard a new environment (e.g. staging) in a different account

**Related docs (day-2 operations):** [`README.md`](README.md) · **Monorepo:** [`../README.md`](../README.md)

> **Shell:** Commands use **bash** (macOS, Linux, or **Git Bash** on Windows). PowerShell variants are noted where syntax differs.

---

## What you are building

```
Internet ──► ALB (HTTPS) ──► UI (:3000)
                    │
                    ├──► API (:8090) ──► Qdrant Cloud + RDS PostgreSQL
                    │
Voice agent ────────┘  RAG_API_BASE_URL=http://api.relaydesk.local:8090
     │
     └──► LiveKit Cloud, Deepgram, Cartesia, xAI, Cal.com
```

| Layer | Provisioned by | Notes |
|-------|----------------|-------|
| VPC, ECS, ALB, RDS, Cognito, ECR, SSM | **Terraform** (`infra/terraform/`) | New per AWS account |
| Qdrant Cloud | **External** | Can reuse existing cluster or create new |
| LiveKit + SIP trunk | **External** | New project or reuse; update SSM |
| LLM / STT / TTS keys | **External** | OpenAI, xAI, Deepgram, Cartesia |
| App images | **Docker → ECR** | Built after Terraform creates registries |
| DB schema + dev seed | **`bootstrap_db.py`** | Destructive reset — dev data only |

---

## Phase 0 — Prerequisites

### AWS account

1. **Do not use the root user.** Create an IAM admin user (or IAM Identity Center) with programmatic access.
2. Configure CLI:

```bash
aws configure --profile relaydesk-admin
# Default region: ap-south-1 (or your chosen region)
```

3. Install locally:

| Tool | Minimum |
|------|---------|
| Terraform | >= 1.5 |
| AWS CLI v2 | Latest |
| Docker | For image builds |
| Python 3.11+ | For `infra/scripts/` |
| `uv` | API / bootstrap scripts |
| Node.js 22 | UI local builds (optional) |
| [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html) | RDS tunnel from laptop |

### External services (before or in parallel with Terraform)

Collect API keys and endpoints. These are **not** created by Terraform.

| Service | Used by | What you need |
|---------|---------|----------------|
| **Qdrant Cloud** | API | `QDRANT_CLUSTER_ENDPOINT`, `QDRANT_API_KEY` |
| **OpenAI** | API embeddings | `OPENAI_API_KEY` |
| **LiveKit Cloud** | API outbound + voice agent | `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, SIP trunk ID |
| **xAI** | Voice agent LLM | `XAI_API_KEY` |
| **Deepgram** | Voice agent STT | `DEEPGRAM_API_KEY` |
| **Cartesia** | Voice agent TTS | `CARTESIA_API_KEY` |
| **Cal.com** | Voice agent scheduling | `CALCOM_API_KEY` |
| **Domain DNS** | UI HTTPS | e.g. Cloudflare for `ui_domain_name` |

### Repository checkout

```bash
git clone <your-repo-url> telephone-agent
cd telephone-agent
```

---

## Phase 1 — Configure Terraform

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` for the **new account**:

| Variable | Action |
|----------|--------|
| `github_org` / `github_repo` | Your GitHub org/user and repo name (OIDC deploy role) |
| `aws_region` | e.g. `ap-south-1` |
| `ui_domain_name` | Production domain (or leave and add later) |
| `rds_master_password` | Set via env on first apply (see below) |
| `voice_agent_desired_count` | `0` to save cost until voice is ready |
| `manage_github_oidc_provider` | `false` if OIDC provider already exists in account |

**First-time RDS password** (required once):

```bash
# bash
export TF_VAR_rds_master_password='YourStrongRdsPassword'

# PowerShell
$env:TF_VAR_rds_master_password = "YourStrongRdsPassword"
```

Optional remote state (recommended for teams):

```bash
cp backend.tf.example backend.tf
# Edit S3 bucket + DynamoDB lock table for this account
```

---

## Phase 2 — Terraform apply (create AWS resources)

```bash
cd infra/terraform
terraform init
terraform plan
terraform apply
```

This creates (among other things):

- VPC, NAT, security groups
- ECS cluster + EC2 ASGs (API, voice)
- ALB + ACM certificate request (if domain set)
- RDS PostgreSQL (private)
- Cognito user pool, UI client, M2M client, role groups
- ECR repositories (api, ui, voice-agent)
- SSM parameter **placeholders**
- Cloud Map internal DNS for API
- IAM roles (ECS tasks, GitHub Actions OIDC)

**Save outputs** — you will need them repeatedly:

```bash
terraform output aws_account_id
terraform output ecs_cluster_name
terraform output ecr_api_repository_url
terraform output ecr_ui_repository_url
terraform output ecr_voice_agent_repository_url
terraform output cognito_user_pool_id
terraform output cognito_ui_client_id
terraform output cognito_callback_urls
terraform output alb_dns_name
terraform output rds_endpoint
terraform output github_actions_role_arn
```

---

## Phase 3 — Local `.env` files (source of truth for SSM)

Fill app env files from Terraform outputs. **Do not commit secrets.**

### `api/.env`

```bash
cd api
cp .env.example .env
```

Set at minimum:

- `OPENAI_API_KEY`
- `QDRANT_CLUSTER_ENDPOINT`, `QDRANT_API_KEY`
- `COGNITO_REGION`, `COGNITO_USER_POOL_ID` — from `terraform output`
- `COGNITO_UI_CLIENT_ID`, `COGNITO_M2M_CLIENT_ID` — from outputs / AWS Console
- `LIVEKIT_*` — if using outbound campaigns
- `OAUTH_DISABLED=false` for production-minded local testing

Leave `DATABASE_URL` as localhost for now; production URL is synced in Phase 4.

### `ui/.env`

```bash
cd ui
cp .env.example .env
```

Set:

- `AUTH_SECRET` — random 32+ char string
- `AUTH_URL` — `https://your-domain` (production) or `http://localhost:3000` (local)
- `COGNITO_ISSUER` — `terraform output cognito_issuer`
- `COGNITO_CLIENT_ID` — UI client id from Terraform
- `COGNITO_CLIENT_SECRET` — Cognito console → App client → Show secret
- `RELAYDESK_API_URL_AWS` — `https://your-domain` (same host as UI; ALB routes `/api` to API)

### `voice-agent/.env`

```bash
cd voice-agent
cp .env.example .env
```

Set LiveKit, xAI, Deepgram, Cartesia, Cal.com keys. For AWS ECS, `RAG_API_BASE_URL` is injected automatically (`http://api.relaydesk.local:8090`). For local dev use `http://127.0.0.1:8090`.

`COGNITO_CLIENT_ID` / `COGNITO_CLIENT_SECRET` — M2M client (voice agent). Secret can be synced from Terraform in Phase 4.

---

## Phase 4 — Sync secrets to SSM

Terraform created empty SSM paths. Upload real values:

```bash
# Preview
python infra/scripts/sync_ssm_parameters.py --dry-run \
  --profile relaydesk-admin --region ap-south-1

# Upload all keys from api/.env, ui/.env, voice-agent/.env
python infra/scripts/sync_ssm_parameters.py \
  --profile relaydesk-admin --region ap-south-1
```

**Production `DATABASE_URL`** (must point at private RDS, not localhost):

```bash
export RDS_DB_PASSWORD='YourStrongRdsPassword'

python infra/scripts/sync_ssm_parameters.py \
  --only DATABASE_URL --from-rds \
  --profile relaydesk-admin --region ap-south-1

# Voice-agent M2M Cognito secret from Terraform state:
python infra/scripts/sync_ssm_parameters.py \
  --only COGNITO_CLIENT_SECRET --from-terraform \
  --profile relaydesk-admin --region ap-south-1
```

After changing SSM, **redeploy** affected ECS services (Phase 6).

---

## Phase 5 — Database bootstrap

RDS starts empty. Initialize schema + Deepak dev seed (destructive — wipes all tables):

1. **Start RDS tunnel** (leave terminal open):

```bash
python infra/scripts/rds_tunnel.py
```

2. **Bootstrap** (second terminal):

```bash
export RDS_DB_PASSWORD='YourStrongRdsPassword'

cd api
uv run python ../infra/scripts/bootstrap_db.py \
  --use-tunnel --password "$RDS_DB_PASSWORD" --yes
```

This runs `drop.sql` → `schema.sql` → `seed_deepak.sql`.

For **production** with real clients, skip seed or replace `seed_deepak.sql` with your own seed — bootstrap always drops all data.

**Verify:** UI → select client `deepakdeshwal85@gmail.com`, or psql via tunnel on `localhost:15432`.

---

## Phase 6 — Build and deploy applications

Ensure Docker is running and ECR login works:

```bash
export PROFILE_NAME="relaydesk-admin"
export AWS_REGION="ap-south-1"

cd infra/terraform
export ACCOUNT_ID="$(terraform output -raw aws_account_id)"
aws ecr get-login-password --profile "$PROFILE_NAME" --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin \
    "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
cd ../..
```

### Option A — deploy scripts (recommended)

```bash
# All services (parallel)
python infra/scripts/deploy_all.py --profile relaydesk-admin --region ap-south-1

# Or one at a time
python infra/scripts/deploy_api.py
python infra/scripts/deploy_ui.py
python infra/scripts/deploy_voice_agent.py
```

### Option B — manual docker push

See [`README.md` § Build images and deploy ECS](README.md#5-build-images-and-deploy-ecs).

Wait until ECS services are **steady** and tasks are **RUNNING**:

```bash
aws ecs describe-services --cluster relaydesk-prod \
  --services relaydesk-prod-api relaydesk-prod-ui relaydesk-prod-voice-agent \
  --profile relaydesk-admin --region ap-south-1 \
  --query 'services[*].{name:serviceName,running:runningCount,desired:desiredCount}'
```

---

## Phase 7 — Custom domain and HTTPS (if using `ui_domain_name`)

1. `terraform apply` with `ui_domain_name` set (Phase 2 may already have done this).
2. Add **ACM validation** CNAME from:

```bash
terraform output acm_dns_validation_records
```

3. Wait for certificate **ISSUED**, then `terraform apply` again if needed.
4. Point domain `@` or `www` **CNAME** to:

```bash
terraform output -raw alb_dns_name
```

5. Cloudflare SSL mode: **Full (strict)**.
6. Confirm Cognito callbacks include production URL:

```bash
terraform output cognito_callback_urls
terraform output cognito_production_sso_ready
```

7. Set `AUTH_URL=https://your-domain` in `ui/.env`, rebuild and redeploy UI.

---

## Phase 8 — Cognito users and roles

New users signing in via SSO land in **`guest-clients`** (view-only).

Promote your admin / test client:

```bash
python infra/scripts/approve_cognito_user.py \
  --email deepakdeshwal85@gmail.com \
  --role relaydesk-admins \
  --business-phone +911171366880 \
  --profile relaydesk-admin --region ap-south-1
```

| Role | Access |
|------|--------|
| `guest-clients` | View-only (default on sign-up) |
| `approved-clients` | Manage consumers, knowledge, campaigns |
| `relaydesk-admins` | Full console + admin pages |

Users must **sign out and sign in** after role changes.

Ensure the user's email exists in PostgreSQL `clients` (bootstrap seed or manual insert) and `client_business_phone_number` is set.

---

## Phase 9 — LiveKit telephony (optional)

If using phone campaigns and inbound voice:

1. Create LiveKit project and **outbound SIP trunk** in LiveKit Cloud.
2. Set `LIVEKIT_*` in `api/.env` and sync SSM.
3. Deploy voice-agent with `voice_agent_desired_count >= 1` in Terraform.
4. Register agent name (`relaydesk-agent` default) in LiveKit Cloud.
5. Map business phone numbers to clients in PostgreSQL.

See [`../voice-agent/README.md`](../voice-agent/README.md) for agent configuration.

---

## Phase 10 — GitHub Actions CI/CD (optional)

1. `terraform output -raw github_actions_role_arn`
2. GitHub repo → **Settings → Secrets and variables → Actions → Variables:**
   - `AWS_REGION` = `ap-south-1`
   - `AWS_ROLE_ARN` = output from step 1
3. Push to `main` — workflow `.github/workflows/deploy-ecs.yml` builds and deploys.

---

## Verification checklist

| Check | How |
|-------|-----|
| API healthy | `curl https://your-domain/api/health` or ALB DNS |
| UI loads | Browser → `https://your-domain` |
| SSO login | Cognito hosted UI / Google if enabled |
| API auth | UI can load consumers after login |
| RDS data | Bootstrap clients visible in UI client picker |
| RAG / Qdrant | Upload a document on Knowledge page |
| Voice agent logs | `aws logs tail /ecs/relaydesk-prod/voice-agent --follow` |
| Scheduled campaigns | Campaigns page → enable schedule → check API poller logs |
| M2M RAG from agent | No `401` in voice-agent logs when calling API |

---

## Order summary (quick checklist)

```
[ ] Phase 0  AWS account + CLI + external API keys
[ ] Phase 1  terraform.tfvars (+ TF_VAR_rds_master_password)
[ ] Phase 2  terraform init && apply
[ ] Phase 3  api/.env, ui/.env, voice-agent/.env
[ ] Phase 4  sync_ssm_parameters.py (+ DATABASE_URL --from-rds)
[ ] Phase 5  rds_tunnel + bootstrap_db.py --yes
[ ] Phase 6  deploy_all.py (or per-service deploy)
[ ] Phase 7  Domain + ACM + redeploy UI
[ ] Phase 8  approve_cognito_user.py
[ ] Phase 9  LiveKit / SIP (if telephony)
[ ] Phase 10 GitHub Actions variables (optional)
```

---

## Changing AWS account — what moves vs what is recreated

| Item | New account? |
|------|----------------|
| Terraform state / all AWS resources | **Recreate** (`terraform apply`) |
| SSM secrets | **Recreate** (`sync_ssm_parameters.py`) |
| ECR images | **Rebuild and push** |
| RDS data | **Recreate** (`bootstrap_db.py` or restore snapshot) |
| Cognito users | **Recreate** (users re-register; re-run `approve_cognito_user.py`) |
| Qdrant collections | **Reuse** same cluster or create new + re-upload docs |
| LiveKit project | **Reuse** or create new project |
| Local `.env` files | **Update** Cognito IDs, URLs; keep vendor API keys if reusing |

---

## Cost-saving while setting up

```bash
# Stop ECS + scale ASGs to 0 while debugging Terraform
python infra/scripts/cost_control.py stop \
  --profile relaydesk-admin --region ap-south-1

# Restore when ready to test
python infra/scripts/cost_control.py start \
  --profile relaydesk-admin --region ap-south-1
```

Set `voice_agent_desired_count = 0` in `terraform.tfvars` until voice testing is needed.

Full teardown of AWS resources: `cd infra/terraform && terraform destroy` (irreversible).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| API cannot connect to RDS | `sync_ssm_parameters.py --only DATABASE_URL --from-rds`, redeploy API |
| UI Cognito redirect error | Match `AUTH_URL` and `terraform output cognito_callback_urls` |
| Voice agent RAG `401` | `sync_ssm_parameters.py --only COGNITO_CLIENT_SECRET --from-terraform`, redeploy voice-agent |
| ECS tasks not starting | Check CloudWatch `/ecs/relaydesk-prod/*` and SSM params exist |
| Empty client list in UI | Run `bootstrap_db.py` or insert `clients` rows |
| Local API against new RDS | `rds_tunnel.py` + `rds_tunnel.py write-env` |

More: [`README.md` § Troubleshooting](README.md#10-troubleshooting).

---

## Related documentation

- [`README.md`](README.md) — ongoing ops, scripts, monitoring
- [`../api/README.md`](../api/README.md) — API local development
- [`../ui/README.md`](../ui/README.md) — UI and auth
- [`../voice-agent/README.md`](../voice-agent/README.md) — voice agent and LiveKit
