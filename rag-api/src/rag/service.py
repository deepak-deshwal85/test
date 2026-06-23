from __future__ import annotations

import logging
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from client_config import ClientConfig
from rag.backends.models import RagSearchHit
from rag.config import RagSettings, load_rag_settings, resolve_qdrant_collection
from rag.ingest import chunk_text, load_documents
from rag.qdrant_store import (
    IndexedChunk,
    QdrantVectorStore,
    new_document_id,
    new_point_id,
)
from rag.embeddings.caching_provider import CachingEmbeddingProvider
from rag.resources import get_embedding_provider, get_qdrant_store

logger = logging.getLogger("agent-telephone-agent")


@dataclass(frozen=True)
class IngestResult:
    collection: str
    document_id: str
    source_uri: str
    chunks_indexed: int


@dataclass(frozen=True)
class EmbeddingResult:
    model: str
    dimensions: int
    embeddings: list[list[float]]
    cache_hits: int = 0
    cache_misses: int = 0


def create_qdrant_store(settings: RagSettings | None = None) -> QdrantVectorStore:
    return get_qdrant_store(settings)


def embed_texts(
    texts: list[str], settings: RagSettings | None = None
) -> EmbeddingResult:
    rag_settings = settings or load_rag_settings()
    provider = get_embedding_provider(rag_settings)
    vectors = provider.embed_texts(texts)

    cache_hits = 0
    cache_misses = 0
    if isinstance(provider, CachingEmbeddingProvider):
        cache_hits = provider.last_cache_hits
        cache_misses = provider.last_cache_misses

    return EmbeddingResult(
        model=rag_settings.embedder_model,
        dimensions=rag_settings.embedder_dimensions,
        embeddings=vectors,
        cache_hits=cache_hits,
        cache_misses=cache_misses,
    )


def ingest_document_path(
    *,
    collection: str,
    source_path: Path,
    settings: RagSettings | None = None,
    store: QdrantVectorStore | None = None,
    max_chars: int = 800,
    overlap: int = 100,
    source_uri: str | None = None,
) -> IngestResult:
    rag_settings = settings or load_rag_settings()
    vector_store = store or create_qdrant_store(rag_settings)
    documents = load_documents(source_path)
    if not documents:
        raise ValueError(f"No ingestible documents found at {source_path}")

    document = documents[0]
    display_uri = source_uri or document.source_uri
    if len(documents) > 1:
        logger.warning(
            "Multiple files in %s; indexing first file %s only via single-path ingest",
            source_path,
            document.source_uri,
        )

    chunks = chunk_text(document.text, max_chars=max_chars, overlap=overlap)
    if not chunks:
        raise ValueError(f"No text chunks produced from {source_path}")

    embedding_result = embed_texts(chunks, rag_settings)
    vector_store.ensure_collection(
        collection,
        vector_size=rag_settings.embedder_dimensions,
    )

    document_id = new_document_id()
    indexed_chunks = [
        IndexedChunk(
            point_id=new_point_id(),
            text=chunk,
            source_uri=display_uri,
            document_id=document_id,
            chunk_index=index,
        )
        for index, chunk in enumerate(chunks)
    ]
    count = vector_store.upsert_chunks(
        collection,
        chunks=indexed_chunks,
        embeddings=embedding_result.embeddings,
    )
    return IngestResult(
        collection=collection,
        document_id=document_id,
        source_uri=display_uri,
        chunks_indexed=count,
    )


def ingest_uploaded_file(
    *,
    collection: str,
    filename: str,
    content: bytes,
    settings: RagSettings | None = None,
    store: QdrantVectorStore | None = None,
) -> IngestResult:
    from tempfile import NamedTemporaryFile

    suffix = Path(filename).suffix.lower() or ".txt"
    with NamedTemporaryFile(delete=False, suffix=suffix) as handle:
        handle.write(content)
        temp_path = Path(handle.name)

    try:
        return ingest_document_path(
            collection=collection,
            source_path=temp_path,
            settings=settings,
            store=store,
            source_uri=filename,
        )
    finally:
        temp_path.unlink(missing_ok=True)


def search_collection(
    *,
    collection: str,
    query: str,
    max_results: int,
    settings: RagSettings | None = None,
    store: QdrantVectorStore | None = None,
) -> list[RagSearchHit]:
    rag_settings = settings or load_rag_settings()
    vector_store = store or create_qdrant_store(rag_settings)
    started = time.perf_counter()

    embed_started = time.perf_counter()
    embedding_result = embed_texts([query], rag_settings)
    query_embedding = embedding_result.embeddings[0]
    embed_ms = (time.perf_counter() - embed_started) * 1000

    qdrant_started = time.perf_counter()
    hits = vector_store.search(
        collection,
        query_vector=query_embedding,
        limit=max_results,
    )
    qdrant_ms = (time.perf_counter() - qdrant_started) * 1000
    total_ms = (time.perf_counter() - started) * 1000

    logger.info(
        "rag search collection=%s hits=%d embed_ms=%.0f qdrant_ms=%.0f total_ms=%.0f "
        "embed_cache_hits=%d embed_cache_misses=%d",
        collection,
        len(hits),
        embed_ms,
        qdrant_ms,
        total_ms,
        embedding_result.cache_hits,
        embedding_result.cache_misses,
    )
    return hits


def search_client_knowledge(
    *,
    client_config: ClientConfig,
    query: str,
    max_results: int,
    settings: RagSettings | None = None,
    store: QdrantVectorStore | None = None,
) -> list[RagSearchHit]:
    collection = resolve_qdrant_collection(client_config, settings)
    return search_collection(
        collection=collection,
        query=query,
        max_results=max_results,
        settings=settings,
        store=store,
    )


def hits_to_payload(hits: list[RagSearchHit]) -> dict[str, object]:
    return {
        "hits": [asdict(hit) for hit in hits],
        "count": len(hits),
    }
