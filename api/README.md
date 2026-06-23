# Telephone Agent RAG API

Layered FastAPI service for embeddings, document ingest, and semantic search over Qdrant. All operations are exposed as HTTP APIs — use Swagger at `/docs` to upload documents, manage collections, and run searches.

## Architecture

```
src/app/
  routers/     HTTP routes (Swagger at /docs)
  services/    Business logic (document parsing, chunking, search)
  db/          Qdrant repository, embedding providers, cache
  schemas/     Pydantic request/response models
  domain/      Internal dataclasses
  core/        Settings, dependencies, collection resolution
```

## Quick start

```powershell
docker compose up -d qdrant
cd api
copy .env.example .env
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8090
```

Or:

```powershell
uv run python -m app
```

Open Swagger UI at [http://127.0.0.1:8090/docs](http://127.0.0.1:8090/docs).

Upload a document via Swagger: **POST** `/v1/collections/{collection}/documents` with a file. For phone `911171366880`, use collection `phone_911171366880`.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/v1/embeddings` | Create embeddings |
| GET | `/v1/embeddings/cache` | Embedding cache stats |
| GET | `/v1/embeddings/cache/lookup?text=...` | Lookup cached embedding |
| DELETE | `/v1/embeddings/cache` | Clear embedding cache |
| DELETE | `/v1/embeddings/cache/entry?text=...` | Delete one cache entry |
| GET | `/v1/collections` | List Qdrant collections |
| GET | `/v1/collections/{collection}` | Collection info |
| DELETE | `/v1/collections/{collection}` | Delete collection |
| POST | `/v1/collections/{collection}/documents` | Upload/index document |
| GET | `/v1/collections/{collection}/documents` | List documents |
| DELETE | `/v1/collections/{collection}/documents/{id}` | Delete document |
| POST | `/v1/search` | Semantic search (`phone_number` or `collection`) |

`phone_number` resolves to collection `phone_{digits}` (e.g. `911171366880` → `phone_911171366880`).

## Environment

Copy `.env.example` to `.env` and set:

- `OPENAI_API_KEY` — required for embeddings
- `QDRANT_URL` — default `http://127.0.0.1:6333`
- `RAG_API_KEY` — optional bearer token for API auth

## Tests

```powershell
uv run pytest
```
