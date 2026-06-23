from __future__ import annotations

from dataclasses import asdict

from app.core.config import Settings
from app.db.embedding_provider import CachingEmbeddingProvider, EmbeddingProviderFactory
from app.domain.models import EmbeddingBatchResult


class EmbeddingService:
    def __init__(
        self,
        settings: Settings,
        provider_factory: EmbeddingProviderFactory,
    ) -> None:
        self._settings = settings
        self._provider_factory = provider_factory

    def create_embeddings(self, texts: list[str]) -> EmbeddingBatchResult:
        provider = self._provider_factory.get_provider()
        vectors = provider.embed_texts(texts)

        cache_hits = 0
        cache_misses = 0
        if isinstance(provider, CachingEmbeddingProvider):
            cache_hits = provider.last_cache_hits
            cache_misses = provider.last_cache_misses

        return EmbeddingBatchResult(
            model=self._settings.embedder_model,
            dimensions=self._settings.embedder_dimensions,
            embeddings=vectors,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
        )

    def lookup_cached(self, text: str) -> list[float] | None:
        cache = self._provider_factory.cache
        if cache is None:
            return None
        provider = self._provider_factory.get_provider()
        return cache.get(provider.config, text)

    def delete_cached(self, text: str) -> bool:
        cache = self._provider_factory.cache
        if cache is None:
            return False
        provider = self._provider_factory.get_provider()
        return cache.delete(provider.config, text)

    def clear_cache(self) -> int:
        cache = self._provider_factory.cache
        if cache is None:
            return 0
        return cache.clear()

    def cache_stats(self) -> dict[str, object]:
        cache = self._provider_factory.cache
        return {
            "enabled": self._settings.embedder_cache_enabled,
            "count": cache.count() if cache else 0,
        }

    @staticmethod
    def to_response(result: EmbeddingBatchResult) -> dict[str, object]:
        return asdict(result)
