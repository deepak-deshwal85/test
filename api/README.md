# RelayDesk API

FastAPI service providing **RAG** (Qdrant vector search, document ingest), **customer management** (PostgreSQL), **outbound call jobs** (LiveKit SIP), and **client profiles**. All routes except `/health` require a Cognito JWT unless `OAUTH_DISABLED=true`.

[← Back to monorepo](../README.md) · **Infrastructure:** [`../infra/README.md`](../infra/README.md)

---

## 1. Description

### What it does

- **RAG:** Upload PDF/text/markdown per phone collection (`phone_<digits>`), embed with OpenAI, search via Qdrant.
- **Customers:** CRUD for client/consumer records scoped by `client_email_id`.
- **Call jobs:** Async outbound dialing of all consumers for a client phone number.
- **Clients:** Profile setup (name, phone, email) after SSO; links Cognito `sub` to tenant.
- **Auth:** Validates Cognito access tokens; UI users are email-scoped; M2M voice-agent tokens bypass tenant checks.

### Architecture

```
src/app/
  routers/     HTTP routes (Swagger at /docs)
  services/    Business logic
  db/          PostgreSQL, Qdrant, embedding providers
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

### Prerequisites

- Python 3.13+, [uv](https://docs.astral.sh/uv/)
- PostgreSQL (local Docker or installed)
- Qdrant (`docker compose up -d qdrant` from repo root)

### Setup database

```bash
cd api
export PGPASSWORD='1234'
psql -U postgres -h localhost -p 5432 -f scripts/init_db.sql
```

### Configure environment

```bash
cp .env.example .env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes (RAG) | OpenAI embeddings |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://user:pass@host:5432/relaydesk` |
| `QDRANT_URL` | Local | `http://127.0.0.1:6333` |
| `QDRANT_CLUSTER_ENDPOINT` | Cloud | HTTPS Qdrant Cloud endpoint (overrides `QDRANT_URL`) |
| `QDRANT_API_KEY` | Cloud | Qdrant Cloud API key |
| `OAUTH_DISABLED` | Local dev | `true` — skip JWT validation |
| `COGNITO_REGION` | Production | e.g. `ap-south-1` |
| `COGNITO_USER_POOL_ID` | Production | User pool ID |
| `COGNITO_UI_CLIENT_ID` | Production | UI OAuth client |
| `COGNITO_M2M_CLIENT_ID` | Production | Voice-agent M2M client |
| `COGNITO_REQUIRED_SCOPE` | Production | Default `relaydesk-api/access` |
| `LIVEKIT_URL` / `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` | Call jobs | Real outbound SIP calls |
| `LIVEKIT_SIP_OUTBOUND_TRUNK_ID` | Call jobs | Outbound trunk ID |
| `LIVEKIT_AGENT_NAME` | Call jobs | Agent dispatch name |
| `CORS_ORIGINS` | Optional | e.g. `http://localhost:3000` |

### Run locally against AWS RDS (SSM tunnel)

RDS is private in AWS. Use two terminals from the **repo root**:

**Terminal 1 — tunnel** (leave open):

```powershell
.\infra\scripts\rds_tunnel.ps1
```

**Terminal 2 — API**:

```powershell
$env:RDS_DB_PASSWORD = "RelayDesk2026!"
.\infra\scripts\write_local_tunnel_database_url.bat
cd api
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8090
```

This writes `api/.env.local` with `DATABASE_URL` pointing at `127.0.0.1:15432`. Requires the [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html) and a running ECS API host. See [`../infra/README.md`](../infra/README.md) for details.

### Start server

```bash
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8090
```

- Swagger: http://127.0.0.1:8090/docs
- Health: http://127.0.0.1:8090/health

### Upload a test document

Use Swagger **POST** `/v1/collections/{collection}/documents` with collection `phone_911171366880` for phone `911171366880`, or:

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
| `scripts/init_db.sql` | Create `relaydesk` database and tables | `psql -U postgres -f scripts/init_db.sql` |
| `scripts/seed_db.sql` | Optional seed data | Run against `relaydesk` DB after init |
| `scripts/migrate_call_job_results.sql` | Add `results_json` to `call_jobs` | For existing DBs upgrading schema |
| `scripts/upload_document.py` | Upload file to a collection via HTTP | `uv run python scripts/upload_document.py --file doc.pdf --collection phone_911171366880` |
| `scripts/reset_qdrant_collections.py` | Delete all Qdrant collections (destructive) | `uv run python scripts/reset_qdrant_collections.py --yes` |
| `scripts/bench_search.py` | Benchmark search latency | `uv run python scripts/bench_search.py --query "hello"` |

### `upload_document.py`

```bash
uv run python scripts/upload_document.py \
  --file path/to/file.pdf \
  --collection phone_911171366880 \
  --base-url http://127.0.0.1:8090
```

Optional: set `RAG_API_KEY` in `.env` if the API requires a bearer token.

### `reset_qdrant_collections.py`

Removes every collection in the configured Qdrant instance. Use only in dev.

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
