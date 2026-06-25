# Telephone Agent API

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
postgresql+asyncpg://postgres:1234@localhost:5432/telephone_agent
```

Create database and tables:

```powershell
cd api
$env:PGPASSWORD='1234'
psql -U postgres -h localhost -p 5432 -f scripts/init_db.sql
```

If the database already exists, connect and run only the `CREATE TABLE` statements from `scripts/init_db.sql`.

Add to `api/.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:1234@localhost:5432/telephone_agent
```

## Quick start

```powershell
docker compose up -d qdrant
cd api
copy .env.example .env
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

Returns `202 Accepted` with `job_id`. The job loads all customers for that `client_phone_number` and places an outbound call to each `consumer_phone_number`.

Set `OUTBOUND_CALL_WEBHOOK_URL` in `.env` to POST call payloads to your telephony provider (LiveKit/SIP). Without it, calls are simulated and logged.

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
| `QDRANT_URL` | Vector store |
| `RAG_API_KEY` | Optional API bearer auth |
| `OUTBOUND_CALL_WEBHOOK_URL` | Optional telephony webhook |

## Tests

```powershell
uv run pytest
```
