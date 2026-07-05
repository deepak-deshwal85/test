from __future__ import annotations

import logging
import uuid
from collections import defaultdict

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.config import Settings
from app.domain.models import DocumentSummary, IndexedChunk, RagSearchHit

logger = logging.getLogger("telephone-rag-api")


class QdrantRepository:
    def __init__(self, settings: Settings, client: QdrantClient | None = None) -> None:
        self._settings = settings
        self._client = client or QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            check_compatibility=False,
            timeout=settings.qdrant_timeout,
        )

    @property
    def client(self) -> QdrantClient:
        return self._client

    def list_collections(self) -> list[str]:
        response = self._client.get_collections()
        return sorted(collection.name for collection in response.collections)

    def get_collection(self, collection_name: str) -> dict[str, object]:
        if not self._client.collection_exists(collection_name):
            raise KeyError(f"Collection {collection_name!r} not found")
        info = self._client.get_collection(collection_name)
        return {
            "name": collection_name,
            "points_count": info.points_count,
            "vector_size": info.config.params.vectors.size,  # type: ignore[union-attr]
        }

    def delete_collection(self, collection_name: str) -> None:
        if not self._client.collection_exists(collection_name):
            raise KeyError(f"Collection {collection_name!r} not found")
        self._client.delete_collection(collection_name)

    def ensure_collection(self, collection_name: str, *, vector_size: int) -> None:
        if self._client.collection_exists(collection_name):
            info = self._client.get_collection(collection_name)
            existing_size = info.config.params.vectors.size  # type: ignore[union-attr]
            if existing_size != vector_size:
                raise ValueError(
                    f"Collection {collection_name} uses vector size {existing_size}, "
                    f"expected {vector_size}."
                )
            return

        self._client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info("created collection %s (dim=%s)", collection_name, vector_size)

    def upsert_chunks(
        self,
        collection_name: str,
        *,
        chunks: list[IndexedChunk],
        embeddings: list[list[float]],
    ) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")

        points = [
            PointStruct(
                id=chunk.point_id,
                vector=embedding,
                payload={
                    "text": chunk.text,
                    "source_uri": chunk.source_uri,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                },
            )
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        self._client.upsert(collection_name=collection_name, points=points)
        return len(points)

    def delete_document(self, collection_name: str, document_id: str) -> None:
        if not self._client.collection_exists(collection_name):
            raise KeyError(f"Collection {collection_name!r} not found")
        self._client.delete(
            collection_name=collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id),
                    )
                ]
            ),
        )

    def list_documents(self, collection_name: str) -> list[DocumentSummary]:
        if not self._client.collection_exists(collection_name):
            return []

        grouped: dict[str, dict[str, object]] = defaultdict(
            lambda: {"source_uri": "", "chunk_count": 0}
        )
        offset = None
        while True:
            points, offset = self._client.scroll(
                collection_name=collection_name,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in points:
                payload = point.payload or {}
                document_id = str(payload.get("document_id") or "")
                if not document_id:
                    continue
                entry = grouped[document_id]
                entry["source_uri"] = str(payload.get("source_uri") or "")
                entry["chunk_count"] = int(entry["chunk_count"]) + 1
            if offset is None:
                break

        return [
            DocumentSummary(
                document_id=document_id,
                source_uri=str(values["source_uri"]),
                chunk_count=int(values["chunk_count"]),
            )
            for document_id, values in sorted(grouped.items())
        ]

    def search(
        self,
        collection_name: str,
        *,
        query_vector: list[float],
        limit: int,
        score_threshold: float | None = None,
    ) -> list[RagSearchHit]:
        try:
            response = self._client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=limit,
                with_payload=True,
                score_threshold=score_threshold,
            )
        except Exception as exc:
            message = str(exc).lower()
            if "not found" in message or "doesn't exist" in message:
                return []
            raise

        hits: list[RagSearchHit] = []
        for result in response.points:
            payload = result.payload or {}
            text = str(payload.get("text") or "")
            if not text:
                continue
            hits.append(
                RagSearchHit(
                    text=text,
                    score=float(result.score or 0.0),
                    source_uri=str(payload.get("source_uri") or "") or None,
                )
            )
        return hits


def new_document_id() -> str:
    return str(uuid.uuid4())


def new_point_id() -> str:
    return str(uuid.uuid4())
