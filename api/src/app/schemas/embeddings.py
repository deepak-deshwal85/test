from __future__ import annotations

from pydantic import BaseModel, Field


class EmbedRequest(BaseModel):
    texts: list[str] = Field(min_length=1, description="Texts to embed")


class EmbedResponse(BaseModel):
    model: str
    dimensions: int
    embeddings: list[list[float]]
    cache_hits: int = 0
    cache_misses: int = 0


class EmbeddingCacheStatsResponse(BaseModel):
    enabled: bool
    count: int


class EmbeddingLookupResponse(BaseModel):
    text: str
    cached: bool
    embedding: list[float] | None = None


class EmbeddingCacheDeleteResponse(BaseModel):
    deleted: bool
    cleared_count: int | None = None
