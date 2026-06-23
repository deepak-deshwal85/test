from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from client_config import ClientConfig

logger = logging.getLogger("agent-telephone-agent")

SUPPORTED_RAG_BACKENDS = frozenset({"xai", "qdrant"})


@dataclass(frozen=True)
class RagClientSettings:
    backend: str
    max_results: int
    rag_api_base_url: str


def load_rag_settings() -> RagClientSettings:
    backend = os.getenv("RAG_BACKEND", "qdrant").strip().lower()
    if backend not in SUPPORTED_RAG_BACKENDS:
        raise ValueError(
            f"Unsupported RAG_BACKEND {backend!r}. Use one of: {sorted(SUPPORTED_RAG_BACKENDS)}"
        )

    return RagClientSettings(
        backend=backend,
        max_results=int(os.getenv("RAG_MAX_RESULTS", "5")),
        rag_api_base_url=os.getenv(
            "RAG_API_BASE_URL", "http://127.0.0.1:8090"
        ).strip().rstrip("/"),
    )


def resolve_rag_backend(
    client_config: ClientConfig,
    settings: RagClientSettings | None = None,
) -> str:
    rag_settings = settings or load_rag_settings()
    if client_config.rag_backend:
        backend = client_config.rag_backend.strip().lower()
    else:
        backend = rag_settings.backend

    if backend not in SUPPORTED_RAG_BACKENDS:
        raise ValueError(
            f"Unsupported rag backend {backend!r} for phone {client_config.phone_number}"
        )
    return backend


def resolve_rag_api_url(
    client_config: ClientConfig,
    settings: RagClientSettings | None = None,
) -> str:
    rag_settings = settings or load_rag_settings()
    if client_config.rag_api_url:
        return client_config.rag_api_url.strip().rstrip("/")
    return rag_settings.rag_api_base_url
