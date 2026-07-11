# RelayDesk API

FastAPI service providing **RAG** (Qdrant vector search, document ingest), **customer management** (PostgreSQL), **outbound call jobs** (LiveKit SIP), and **client profiles**. All routes except `/health` require a Cognito JWT unless `OAUTH_DISABLED=true`.

[← Back to monorepo](../README.md) · **Infrastructure:** [`../infra/README.md`](../infra/README.md)

---

## 1. Description

### What it does

- **RAG:** Upload PDF/text/markdown per phone collection (`phone_<digits>`), embed with OpenAI, search via Qdrant Cloud.
- **Customers:** CRUD for client/consumer records scoped by `client_email_id`.
- **Call jobs:** Async outbound dialing of all consumers for a client phone number.
- **Clients:** Profile setup (name, phone, email) after SSO; links Cognito `sub` to tenant.
- **Auth:** Validates Cognito access tokens; UI users are email-scoped; M2M voice-agent tokens bypass tenant checks.

### Architecture

```
src/app/
  routers/     HTTP routes (Swagger at /docs)
  services/    Business logic
  db/          PostgreSQL (RDS), Qdrant Cloud, embedding providers
  schemas/     Pydantic request/response models
  domain/      Internal dataclasses
  core/        Settings, OAuth, RBAC, tenant scoping
```

### Key API groups

| Prefix | Purpose |
|--------|---------|
| `/health` | Liveness (no auth) |
| `/v1/collections`, `/v1/search` | RAG — collections, documents, semantic search |
| `/v1/customers` | Customer CRUD + approve |
| `/v1/call-jobs` | Trigger and poll outbound campaigns |
| `/v1/clients` | Client profile (`/me`, `/profile`) |
| `/v1/embeddings` | Embedding cache (admin) |

---

## 2. Run locally

Local development uses **AWS RDS** (SSM tunnel) and **Qdrant Cloud** — the same managed backends as production.

### Prerequisites

- Python 3.13+, [uv](https://docs.astral.sh/uv/)
- [AWS CLI](https://aws.amazon.com/cli/) + profile (e.g. `relaydesk-admin`)
- [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html) for the RDS tunnel
- Qdrant Cloud cluster + API key
- OpenAI API key (embeddings)

### Configure environment

```bash
cd api
cp .env.example .env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes (RAG) | OpenAI embeddings |
| `DATABASE_URL` | Yes | RDS via tunnel: `...@127.0.0.1:15432/relaydesk` (see below) |
| `QDRANT_CLUSTER_ENDPOINT` | Yes | Qdrant Cloud HTTPS endpoint |
| `QDRANT_API_KEY` | Yes | Qdrant Cloud API key |
| `QDRANT_CLUSTER_NAME` | Optional | Cluster label (error messages) |
| `OAUTH_DISABLED` | Local dev | `true` — skip JWT validation |
| `COGNITO_*` | Production / SSO | User pool and client IDs |
| `LIVEKIT_*` | Call jobs | Real outbound SIP calls |
| `CORS_ORIGINS` | Optional | e.g. `http://localhost:3000` |

### Start (Windows)

**Terminal 1 — RDS tunnel** (leave open):

```powershell
.\infra\scripts\rds_tunnel.ps1
```

**Terminal 2 — API**:

```powershell
$env:RDS_DB_PASSWORD = "YourRdsPassword"
.\infra\scripts\start_local_api.bat
```

Or manually:

```powershell
$env:RDS_DB_PASSWORD = "YourRdsPassword"
.\infra\scripts\write_local_tunnel_database_url.bat
cd api
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8090
```

`write_local_tunnel_database_url.bat` writes `api/.env.local` with `DATABASE_URL` pointing at `127.0.0.1:15432`.

### Initialize database (first time / fresh RDS)

The API **does not** create tables on startup. After RDS exists and `DATABASE_URL` is configured, run once:

```powershell
$env:RDS_DB_PASSWORD = "YourRdsPassword"
python infra/scripts/init_database.py --use-tunnel
```

Or from `api/`:

```bash
uv run python scripts/init_db.py              # schema + dummy seed
uv run python scripts/init_db.py --schema-only
```

Seed includes `acme@example.com`, 3 customers, and 2 call jobs (idempotent).

**Drop and recreate** (destructive — deletes all rows):

```powershell
$env:RDS_DB_PASSWORD = "YourRdsPassword"
python infra/scripts/reset_database.py --use-tunnel --yes
```

Or from `api/`: `uv run python scripts/reset_db.py --yes`

### Start (Git Bash / macOS / Linux)

```bash
# Terminal 1
./infra/scripts/rds_tunnel.sh

# Terminal 2
export RDS_DB_PASSWORD='YourRdsPassword'
python infra/scripts/write_local_tunnel_database_url.py --password "$RDS_DB_PASSWORD"
cd api && uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8090
```

- Swagger: http://127.0.0.1:8090/docs
- Health: http://127.0.0.1:8090/health

### Upload a test document

```bash
uv run python scripts/upload_document.py \
  --file ./data/sample.pdf \
  --collection phone_911171366880 \
  --base-url http://127.0.0.1:8090
```

---

## 3. Docker build, push to ECR, update ECS

Run from **repo root** in one shell session (Git Bash). **Wait for `docker build` to finish successfully** before pushing.

```bash
export PROFILE_NAME="relaydesk-admin"
export AWS_REGION="ap-south-1"
export IMAGE_TAG="latest"    # match api_ecr_image_tag in terraform.tfvars

cd infra/terraform
export ACCOUNT_ID="$(terraform output -raw aws_account_id)"
export ECR_API="$(terraform output -raw ecr_api_repository_url)"
export CLUSTER="$(terraform output -raw ecs_cluster_name)"
export SERVICE="$(terraform output -raw ecs_service_api_name)"
cd ../..

aws ecr get-login-password --profile "$PROFILE_NAME" --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin \
    "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

docker build -t relaydesk-api:latest ./api
docker tag relaydesk-api:latest "${ECR_API}:${IMAGE_TAG}"
docker tag relaydesk-api:latest "${ECR_API}:latest"
docker push "${ECR_API}:${IMAGE_TAG}"
docker push "${ECR_API}:latest"

aws ecs update-service \
  --cluster "$CLUSTER" \
  --service "$SERVICE" \
  --force-new-deployment \
  --profile "$PROFILE_NAME" \
  --region "$AWS_REGION"
```

After deploy, tail logs:

```bash
aws logs tail /ecs/relaydesk-prod/api --since 10m --follow \
  --region "$AWS_REGION" --profile "$PROFILE_NAME"
```

**Secrets:** API reads from SSM Parameter Store (`/relaydesk/prod/api/*`). Sync with [`../infra/scripts/sync_ssm_parameters.py`](../infra/scripts/sync_ssm_parameters.py). See [`../infra/README.md`](../infra/README.md).

---

## 4. Scripts

All scripts run from the `api/` directory unless noted.

| Script | Purpose | Usage |
|--------|---------|--------|
| `scripts/init_db.py` | Create tables + optional dummy seed data | `uv run python scripts/init_db.py` |
| `scripts/reset_db.py` | **Drop all tables**, recreate schema + seed | `uv run python scripts/reset_db.py --yes` |
| `scripts/db/drop.sql` | Drop `call_jobs`, `customers`, `clients` | Used by `reset_db.py` |
| `scripts/db/schema.sql` | Idempotent DDL (clients, customers, call_jobs) | Used by `init_db.py` / `reset_db.py` |
| `scripts/db/seed.sql` | Dummy dev rows (Acme client, 3 customers, 2 call jobs) | Used by `init_db.py` |
| `scripts/init_db.sql` | Deprecated pointer | Use `init_db.py` instead |
| `scripts/migrate_db.py` | Apply SQL migrations to existing DB | `uv run python scripts/migrate_db.py` |
| `scripts/db/migrate_customer_campaign.sql` | Add `call_schedule` + `status` columns | Used by `migrate_db.py` |
| `scripts/upload_document.py` | Upload file to a collection via HTTP | `uv run python scripts/upload_document.py --file doc.pdf --collection phone_911171366880` |
| `scripts/reset_qdrant_collections.py` | Delete all Qdrant Cloud collections (destructive) | `uv run python scripts/reset_qdrant_collections.py --yes` |
| `scripts/bench_search.py` | Benchmark search latency | `uv run python scripts/bench_search.py --query "hello"` |

### Infra helpers (repo root)

| Script | Purpose |
|--------|---------|
| [`../infra/scripts/rds_tunnel.ps1`](../infra/scripts/rds_tunnel.ps1) | SSM port-forward to RDS on `localhost:15432` |
| [`../infra/scripts/write_local_tunnel_database_url.bat`](../infra/scripts/write_local_tunnel_database_url.bat) | Write `api/.env.local` with tunnel `DATABASE_URL` |
| [`../infra/scripts/start_local_api.bat`](../infra/scripts/start_local_api.bat) | Tunnel env + start API |

### `reset_qdrant_collections.py`

Removes every collection in the configured Qdrant Cloud cluster. Use only in dev.

```bash
uv run python scripts/reset_qdrant_collections.py --dry-run
uv run python scripts/reset_qdrant_collections.py --yes
```

---

## Tests

```bash
uv run pytest
uv run ruff check src tests
uv run ruff format src tests
```
