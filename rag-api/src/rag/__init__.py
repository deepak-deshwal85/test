"""RAG REST API service (Qdrant + embeddings + document ingest)."""

from rag.config import (
    RagSettings,
    load_rag_settings,
    resolve_qdrant_collection,
    resolve_rag_backend,
)

__all__ = [
    "RagSettings",
    "load_rag_settings",
    "resolve_qdrant_collection",
    "resolve_rag_backend",
]
