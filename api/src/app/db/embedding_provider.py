from __future__ import annotations

import logging

from app.core.config import Settings
from app.db.embedding_cache_repository import EmbeddingCacheRepository
from app.db.embeddings.base import EmbeddingConfig, EmbeddingProvider
from app.db.embeddings.openai_provider import OpenAIEmbeddingProvider

logger = logging.getLogger("relaydesk-api")


class CachingEmbeddingProvider:
    def __init__(
        self,
        inner: EmbeddingProvider,
        cache: EmbeddingCacheRepository,
    ) -> None:
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
            if hasattr(self._cache, "put_many"):
                self._cache.put_many(
                    self._inner.config,
                    [(miss_texts[i], fresh_vectors[i]) for i in range(len(miss_texts))],
                )
            else:
                for index, vector in zip(miss_indices, fresh_vectors, strict=True):
                    self._cache.put(self._inner.config, texts[index], vector)

        final = [v for v in results if v is not None]
        if len(final) != len(texts):
            raise RuntimeError(
                f"Embedding count mismatch: got {len(final)}, expected {len(texts)}"
            )
        return final


class EmbeddingProviderFactory:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._provider: EmbeddingProvider | None = None
        self._cache: EmbeddingCacheRepository | None = None

    @property
    def cache(self) -> EmbeddingCacheRepository | None:
        if not self._settings.embedder_cache_enabled:
            return None
        if self._cache is None:
            self._cache = EmbeddingCacheRepository(self._settings.embedder_cache_path)
        return self._cache

    def get_provider(self) -> EmbeddingProvider:
        if self._provider is None:
            config = EmbeddingConfig(
                provider=self._settings.embedder_provider,
                model=self._settings.embedder_model,
                dimensions=self._settings.embedder_dimensions,
            )
            inner = OpenAIEmbeddingProvider(
                config,
                api_key=self._settings.openai_api_key,
                base_url=self._settings.openai_base_url,
                timeout=self._settings.openai_timeout,
            )
            if self._settings.embedder_cache_enabled:
                cache = self.cache
                assert cache is not None
                self._provider = CachingEmbeddingProvider(inner, cache)
            else:
                self._provider = inner
            logger.info(
                "embedding provider ready model=%s dim=%s cache=%s",
                config.model,
                config.dimensions,
                self._settings.embedder_cache_enabled,
            )
        return self._provider
