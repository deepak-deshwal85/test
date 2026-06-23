from __future__ import annotations

import logging
import time
from dataclasses import asdict

from app.core.collections import resolve_collection
from app.core.config import Settings
from app.db.qdrant_repository import QdrantRepository
from app.domain.models import RagSearchHit
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger("telephone-rag-api")


class SearchService:
    def __init__(
        self,
        settings: Settings,
        qdrant: QdrantRepository,
        embedding_service: EmbeddingService,
    ) -> None:
        self._settings = settings
        self._qdrant = qdrant
        self._embedding_service = embedding_service

    def search(
        self,
        *,
        query: str,
        max_results: int | None,
        collection: str | None = None,
        phone_number: str | None = None,
    ) -> tuple[list[RagSearchHit], str]:
        limit = max_results or self._settings.rag_max_results
        started = time.perf_counter()
        resolved_collection = resolve_collection(
            phone_number=phone_number,
            collection=collection,
        )

        embed_started = time.perf_counter()
        embedding_result = self._embedding_service.create_embeddings([query])
        query_vector = embedding_result.embeddings[0]
        embed_ms = (time.perf_counter() - embed_started) * 1000

        qdrant_started = time.perf_counter()
        hits = self._qdrant.search(
            resolved_collection,
            query_vector=query_vector,
            limit=limit,
        )
        qdrant_ms = (time.perf_counter() - qdrant_started) * 1000
        total_ms = (time.perf_counter() - started) * 1000

        logger.info(
            "search collection=%s hits=%d embed_ms=%.0f qdrant_ms=%.0f total_ms=%.0f "
            "embed_cache_hits=%d embed_cache_misses=%d phone=%s",
            resolved_collection,
            len(hits),
            embed_ms,
            qdrant_ms,
            total_ms,
            embedding_result.cache_hits,
            embedding_result.cache_misses,
            phone_number,
        )
        return hits, resolved_collection

    @staticmethod
    def hits_to_response(
        hits: list[RagSearchHit], collection: str
    ) -> dict[str, object]:
        return {
            "hits": [asdict(hit) for hit in hits],
            "count": len(hits),
            "collection": collection,
        }
