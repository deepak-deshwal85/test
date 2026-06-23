# Telephone Agent Monorepo

This repository contains two independent Python projects:

| Folder | Purpose |
|--------|---------|
| [`voice-agent/`](voice-agent/) | LiveKit voice agent (STT, LLM, TTS, Cal.com scheduling) |
| [`api/`](api/) | RAG REST API (Qdrant, embeddings, document ingest, search) |

The voice agent calls the RAG API over HTTP. Each project has its own `pyproject.toml`, dependencies, tests, and README.

## Quick start (local)

### 1. Start Qdrant

```powershell
docker compose up -d qdrant
```

### 2. Start RAG API

```powershell
cd api
copy .env.example .env
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8090
```

API docs: http://127.0.0.1:8090/docs

### 3. Upload documents (via Swagger)

Open http://127.0.0.1:8090/docs and use **POST** `/v1/collections/{collection}/documents` to upload a PDF or text file. For phone `911171366880`, use collection `phone_911171366880`.

### 4. Start voice agent

```powershell
cd voice-agent
copy .env.example .env
uv sync
uv run python src/agent.py download-files
uv run python src/agent.py console
```

Set `RAG_API_BASE_URL=http://127.0.0.1:8090` in `voice-agent/.env`.

## Project layout

```
telephone-agent/
├── voice-agent/          # LiveKit voice agent
│   ├── src/
│   ├── config/           # Per-phone client configs
│   ├── tests/
│   └── README.md
├── api/                  # Layered RAG REST API + Qdrant
│   ├── src/app/
│   ├── data/
│   ├── tests/
│   └── README.md
├── docker-compose.yml    # Qdrant (+ optional api)
└── README.md
```

## AWS deployment (summary)

- **voice-agent** → LiveKit Cloud (`lk agent create`)
- **api** → ECS Fargate or EC2
- **Qdrant** → Qdrant Cloud or ECS with persistent volume

See each project's README for details.

## Development

```powershell
cd voice-agent; uv run pytest
cd api; uv run pytest
```

See [AGENTS.md](AGENTS.md) for LiveKit agent development guidelines.
