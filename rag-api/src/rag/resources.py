from __future__ import annotations

import logging
import os

from rag.config import RagSettings, load_rag_settings
from rag.embeddings import EmbeddingProvider, create_embedding_provider
from rag.qdrant_store import QdrantVectorStore

logger = logging.getLogger("agent-telephone-agent")

_embedding_provider: EmbeddingProvider | None = None
_qdrant_store: QdrantVectorStore | None = None


def get_embedding_provider(settings: RagSettings | None = None) -> EmbeddingProvider:
    global _embedding_provider
    if _embedding_provider is None:
        rag_settings = settings or load_rag_settings()
        _embedding_provider = create_embedding_provider(
            provider=rag_settings.embedder_provider,
            model=rag_settings.embedder_model,
            dimensions=rag_settings.embedder_dimensions,
            cache_enabled=rag_settings.embedder_cache_enabled,
            cache_path=rag_settings.embedder_cache_path,
        )
        logger.info(
            "initialized shared embedding provider model=%s dim=%s cache=%s path=%s",
            rag_settings.embedder_model,
            rag_settings.embedder_dimensions,
            rag_settings.embedder_cache_enabled,
            rag_settings.embedder_cache_path,
        )
    return _embedding_provider


def get_qdrant_store(settings: RagSettings | None = None) -> QdrantVectorStore:
    global _qdrant_store
    if _qdrant_store is None:
        rag_settings = settings or load_rag_settings()
        _qdrant_store = QdrantVectorStore(
            url=rag_settings.qdrant_url,
            api_key=os.getenv("QDRANT_API_KEY", "").strip() or None,
        )
        logger.info("initialized shared Qdrant client url=%s", rag_settings.qdrant_url)
    return _qdrant_store
