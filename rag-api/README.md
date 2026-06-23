# RAG API

Standalone REST API for document ingestion, embedding, vector search, and Qdrant storage. Used by the [voice agent](../voice-agent/) over HTTP.

## Features

- Upload PDF/TXT/MD documents → chunk → embed → store in Qdrant
- Semantic search by phone number or collection name
- OpenAI embeddings with persistent query cache
- Per-phone Qdrant collections (`phone_<digits>`)

## Setup

```powershell
cd rag-api
uv sync
copy .env.example .env
docker compose -f ../docker-compose.yml up -d qdrant
```

Fill in `.env`:

```env
OPENAI_API_KEY=sk-...
QDRANT_URL=http://127.0.0.1:6333
RAG_API_HOST=127.0.0.1
RAG_API_PORT=8090
```

## Run

```powershell
uv run python scripts/run_rag_api.py
```

API docs: http://127.0.0.1:8090/docs

## Upload documents

```powershell
uv run python scripts/upload_rag_document.py --phone 911171366880 --file knowledge_base/reliance.pdf
```

Or via REST:

```powershell
curl -X POST "http://127.0.0.1:8090/v1/collections/phone_911171366880/documents" -F "file=@knowledge_base/reliance.pdf"
```

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Health check |
| `POST` | `/v1/embeddings` | Create embeddings for text array |
| `POST` | `/v1/collections/{collection}/documents` | Upload and index a document |
| `POST` | `/v1/search` | Search (`phone_number` or `collection` + `query`) |
| `DELETE` | `/v1/collections/{collection}/documents/{document_id}` | Delete a document |

### Search example

```json
POST /v1/search
{
  "phone_number": "911171366880",
  "query": "Reliance annual revenue",
  "max_results": 5
}
```

## Inspect Qdrant data

- **Web UI:** http://127.0.0.1:6333/dashboard
- **Collection:** `phone_911171366880` (default per phone config)

```powershell
curl http://127.0.0.1:6333/collections/phone_911171366880
```

## Configuration

### `config/rag.properties`

| Key | Purpose |
|-----|---------|
| `rag.backend` | `qdrant` |
| `rag.max_results` | Default search limit |
| `rag.embedder.*` | OpenAI embedding model settings |
| `qdrant.url` | Qdrant server URL |

### Phone config (`config/phone_number_<digits>.json`)

Used to resolve collection name and client metadata during upload/search.

## Docker

```powershell
docker build -t telephone-rag-api .
docker run -p 8090:8090 --env-file .env telephone-rag-api
```

## Project structure

```
rag-api/
├── src/
│   ├── rag/
│   │   ├── api_server.py     # FastAPI app
│   │   ├── service.py        # Ingest + search logic
│   │   ├── qdrant_store.py
│   │   ├── embeddings/
│   │   └── ...
│   ├── client_config.py
│   └── paths.py
├── config/
│   ├── rag.properties
│   └── phone_number_*.json
├── knowledge_base/
├── scripts/
├── tests/
└── Dockerfile
```

## Tests

```powershell
uv run pytest
```

## AWS deployment

Run as a container on ECS Fargate with:

- `QDRANT_URL` pointing to Qdrant Cloud or a private Qdrant instance
- `OPENAI_API_KEY` in Secrets Manager
- Optional `RAG_API_KEY` for auth
- ALB health check on `/health`

The voice agent only needs `RAG_API_BASE_URL` — it never connects to Qdrant directly.
