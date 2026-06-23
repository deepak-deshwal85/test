import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rag.embeddings.base import EmbeddingConfig
from rag.embeddings.cache import EmbeddingCache, normalize_cache_text
from rag.embeddings.caching_provider import CachingEmbeddingProvider


class FakeEmbeddingProvider:
    def __init__(self) -> None:
        self.config = EmbeddingConfig(
            provider="openai",
            model="text-embedding-3-small",
            dimensions=3,
        )
        self.calls: list[list[str]] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [[float(index), 0.5, 0.25] for index in range(len(texts))]


def test_normalize_cache_text_is_case_insensitive():
    assert normalize_cache_text("  Qualification? ") == "qualification"


def test_embedding_cache_reuses_stored_vectors(tmp_path: Path):
    cache = EmbeddingCache(tmp_path / "cache.sqlite")
    config = EmbeddingConfig(provider="openai", model="m1", dimensions=3)
    cache.put(config, "skills", [1.0, 2.0, 3.0])
    assert cache.get(config, "Skills") == [1.0, 2.0, 3.0]
    cache.close()


def test_caching_provider_hits_cache_on_repeat_query(tmp_path: Path):
    inner = FakeEmbeddingProvider()
    cache = EmbeddingCache(tmp_path / "cache.sqlite")
    provider = CachingEmbeddingProvider(inner, cache)

    first = provider.embed_texts(["qualification"])
    second = provider.embed_texts(["Qualification?"])

    assert first == second
    assert len(inner.calls) == 1
    assert provider.last_cache_hits == 1
    assert provider.last_cache_misses == 0

    provider.close()


def test_caching_provider_batches_cache_misses(tmp_path: Path):
    inner = FakeEmbeddingProvider()
    cache = EmbeddingCache(tmp_path / "cache.sqlite")
    provider = CachingEmbeddingProvider(inner, cache)

    vectors = provider.embed_texts(["alpha", "beta"])

    assert len(vectors) == 2
    assert len(inner.calls) == 1
    assert inner.calls[0] == ["alpha", "beta"]
    assert provider.last_cache_misses == 2

    provider.embed_texts(["alpha", "beta"])
    assert len(inner.calls) == 1
    assert provider.last_cache_hits == 2

    provider.close()
