# RelayDesk API

Layered FastAPI service: RAG (Qdrant), customer CRUD (PostgreSQL), and async outbound call jobs.

## Architecture

```
src/app/
  routers/     HTTP routes (Swagger at /docs)
  services/    Business logic
  db/          PostgreSQL + Qdrant + embedding providers
  schemas/     Pydantic request/response models
  domain/      Internal dataclasses
  core/        Settings, dependencies
```

## Database setup (PostgreSQL)

Default connection (override in `.env`):

```
postgresql+asyncpg://postgres:1234@localhost:5432/relaydesk
```

Create database and tables:

```bash
cd api
export PGPASSWORD='1234'
psql -U postgres -h localhost -p 5432 -f scripts/init_db.sql
```

If the database already exists, connect and run only the `CREATE TABLE` statements from `scripts/init_db.sql`.

Add to `api/.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:1234@localhost:5432/relaydesk
```

## Quick start

```bash
docker compose up -d qdrant
cd api
cp .env.example .env
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8090
```

Swagger: http://127.0.0.1:8090/docs

## Customer APIs

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/customers` | Create customer |
| GET | `/v1/customers` | List customers (`?client_phone_number=`) |
| GET | `/v1/customers/{id}` | Get customer |
| PUT | `/v1/customers/{id}` | Update customer |
| DELETE | `/v1/customers/{id}` | Delete customer |

**Customer fields:** `client_phone_number`, `client_name`, `consumer_phone_number`

Example create:

```json
{
  "client_phone_number": "911171366880",
  "client_name": "Acme Corp",
  "consumer_phone_number": "9876543210"
}
```

## Call job APIs

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/call-jobs/trigger` | Async trigger — calls all consumers for a client |
| GET | `/v1/call-jobs/{job_id}` | Poll job status |

**Trigger request:**

```json
{
  "client_phone_number": "911171366880"
}
```

Returns `202 Accepted` with `job_id`. The job loads all customers for that `client_phone_number` and dials each `consumer_phone_number`.

**Console logs** show each step (`call job loaded customers`, `call attempt`, etc.). **GET** `/v1/call-jobs/{job_id}` returns a `results` array with per-customer call details.

### Real calls (LiveKit SIP)

Add to `api/.env` (same LiveKit project as voice-agent):

```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
LIVEKIT_SIP_OUTBOUND_TRUNK_ID=ST_xxxx   # outbound trunk from LiveKit Cloud / lk CLI
LIVEKIT_AGENT_NAME=relaydesk
```

Without these, calls are **simulated only** (job completes but no phone rings).

The voice agent must be running (`uv run python src/agent.py dev`) to answer outbound rooms.

## RAG APIs

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/v1/embeddings` | Create embeddings |
| POST | `/v1/collections/{collection}/documents` | Upload document |
| POST | `/v1/search` | Semantic search |
| ... | | See Swagger for full list |

## Environment

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Embeddings |
| `DATABASE_URL` | PostgreSQL async connection |
| `QDRANT_URL` | Local Qdrant (default `http://127.0.0.1:6333`) |
| `QDRANT_CLUSTER_ENDPOINT` | Qdrant Cloud HTTPS endpoint (overrides `QDRANT_URL`) |
| `QDRANT_API_KEY` | Required for Qdrant Cloud |
| `COGNITO_REGION` / `COGNITO_USER_POOL_ID` | Cognito issuer setup for JWT validation |
| `COGNITO_UI_CLIENT_ID` / `COGNITO_M2M_CLIENT_ID` | Allowed OAuth clients (UI + voice M2M) |
| `COGNITO_REQUIRED_SCOPE` | Required access scope (default `relaydesk-api/access`) |
| `OUTBOUND_CALL_WEBHOOK_URL` | Legacy optional webhook (use LiveKit vars instead) |
| `LIVEKIT_URL` / `LIVEKIT_API_KEY` / `LIVEKIT_API_SECRET` | Required for real outbound calls |
| `LIVEKIT_SIP_OUTBOUND_TRUNK_ID` | Outbound SIP trunk ID |
| `LIVEKIT_AGENT_NAME` | Agent to dispatch (default `relaydesk`) |

## Tests

```bash
uv run pytest
```
