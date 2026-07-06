# Voice Agent

RelayDesk LiveKit voice agent for phone calls. Handles speech-to-text, LLM reasoning, text-to-speech, Cal.com meeting scheduling, and document Q&A via the [RAG API](../api/).

## Features

- LiveKit Agents pipeline (Deepgram STT, xAI LLM, Cartesia TTS)
- Per-phone client configuration (`config/phone_number_<digits>.json`)
- Cal.com meeting booking tools
- Automatic document search on every user turn (calls RAG API)
- xAI FileSearch fallback (`RAG_BACKEND=xai`)

## Setup

```powershell
cd voice-agent
uv sync
copy .env.example .env
```

Fill in `.env`:

```env
LIVEKIT_URL=wss://...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...

XAI_API_KEY=...
DEEPGRAM_API_KEY=...
CARTESIA_API_KEY=...
CALCOM_API_KEY=...

RAG_BACKEND=qdrant
RAG_API_BASE_URL=http://127.0.0.1:8090
CLIENT_PHONE_OVERRIDE=+911171366880
```

## Run

Start [api](../api/) first, then:

```powershell
uv run python src/agent.py download-files
uv run python src/agent.py console
```

For telephony / LiveKit Cloud:

```powershell
uv run python src/agent.py dev
```

Deploy to LiveKit Cloud:

```powershell
lk agent create
```

## Configuration

### Phone config (`config/phone_number_<digits>.json`)

```json
{
  "phone_number": "911171366880",
  "client_name": "Deepak Kumar",
  "knowledge_base_topic": "Reliance Industries",
  "xai_collection_id": "collection_...",
  "calcom_username": "...",
  "calcom_event_type_slug": "30min",
  "calcom_event_type_id": 6073963,
  "rag_backend": "qdrant",
  "rag_api_url": "http://127.0.0.1:8090"
}
```

### RAG client env vars

| Variable | Purpose |
|----------|---------|
| `RAG_BACKEND` | `qdrant` (RAG API) or `xai` (FileSearch) |
| `RAG_API_BASE_URL` | RAG API URL when using `qdrant` |
| `RAG_API_KEY` | Optional bearer token for RAG API |
| `RAG_MAX_RESULTS` | Max search hits (default 5) |

## Project structure

```
voice-agent/
├── src/
│   ├── agent.py              # Entry point
│   ├── agent_instructions.py
│   ├── client_config.py
│   ├── scheduling_tools.py
│   ├── rag_client/           # HTTP client for RAG API
│   └── ...
├── config/
├── tests/
├── Dockerfile
└── livekit.toml
```

## Tests

```powershell
uv run pytest
```
