from __future__ import annotations

import logging

from rag.embeddings.base import EmbeddingConfig, EmbeddingProvider
from rag.embeddings.cache import EmbeddingCache

logger = logging.getLogger("agent-telephone-agent")


class CachingEmbeddingProvider:
    """Wraps an embedding provider with a persistent on-disk cache."""

    def __init__(self, inner: EmbeddingProvider, cache: EmbeddingCache) -> None:
        self._inner = inner
        self._cache = cache
        self.last_cache_hits = 0
        self.last_cache_misses = 0

    @property
    def config(self) -> EmbeddingConfig:
        return self._inner.config

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        self.last_cache_hits = 0
        self.last_cache_misses = 0
        results: list[list[float] | None] = [None] * len(texts)
        miss_indices: list[int] = []
        miss_texts: list[str] = []

        for index, text in enumerate(texts):
            cached = self._cache.get(self._inner.config, text)
            if cached is not None:
                results[index] = cached
                self.last_cache_hits += 1
            else:
                miss_indices.append(index)
                miss_texts.append(text)
                self.last_cache_misses += 1

        if miss_texts:
            fresh_vectors = self._inner.embed_texts(miss_texts)
            for index, vector in zip(miss_indices, fresh_vectors, strict=True):
                results[index] = vector
                self._cache.put(self._inner.config, texts[index], vector)

        if self.last_cache_hits:
            logger.debug(
                "embedding cache hits=%d misses=%d",
                self.last_cache_hits,
                self.last_cache_misses,
            )

        return [vector for vector in results if vector is not None]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def close(self) -> None:
        if hasattr(self._inner, "close"):
            self._inner.close()  # type: ignore[attr-defined]
        self._cache.close()
