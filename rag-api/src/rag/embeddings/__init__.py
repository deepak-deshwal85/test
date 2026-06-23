from __future__ import annotations

from pathlib import Path

from rag.embeddings.base import EmbeddingConfig, EmbeddingProvider
from rag.embeddings.caching_provider import CachingEmbeddingProvider
from rag.embeddings.cache import EmbeddingCache
from rag.embeddings.openai_provider import OpenAIEmbeddingProvider

__all__ = [
    "EmbeddingConfig",
    "EmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "create_embedding_provider",
]


def create_embedding_provider(
    *,
    provider: str,
    model: str,
    dimensions: int,
    cache_enabled: bool = False,
    cache_path: Path | None = None,
) -> EmbeddingProvider:
    normalized = provider.strip().lower()
    if normalized == "openai":
        inner: EmbeddingProvider = OpenAIEmbeddingProvider(
            EmbeddingConfig(provider=normalized, model=model, dimensions=dimensions)
        )
    else:
        raise ValueError(
            f"Unsupported rag.embedder.provider {provider!r}. Supported: openai"
        )

    if cache_enabled:
        if cache_path is None:
            raise ValueError("cache_path is required when cache_enabled is true")
        return CachingEmbeddingProvider(inner, EmbeddingCache(cache_path))

    return inner
