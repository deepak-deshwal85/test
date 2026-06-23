from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RagSearchHit:
    text: str
    score: float
    source_uri: str | None = None


@dataclass(frozen=True)
class IndexedChunk:
    point_id: str
    text: str
    source_uri: str
    document_id: str
    chunk_index: int


@dataclass(frozen=True)
class IngestResult:
    collection: str
    document_id: str
    source_uri: str
    chunks_indexed: int


@dataclass(frozen=True)
class EmbeddingBatchResult:
    model: str
    dimensions: int
    embeddings: list[list[float]]
    cache_hits: int = 0
    cache_misses: int = 0


@dataclass(frozen=True)
class DocumentSummary:
    document_id: str
    source_uri: str
    chunk_count: int
