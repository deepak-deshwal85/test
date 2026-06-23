from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from rag.backends.models import RagSearchHit

logger = logging.getLogger("agent-telephone-agent")


@dataclass(frozen=True)
class IndexedChunk:
    point_id: str
    text: str
    source_uri: str
    document_id: str
    chunk_index: int


class QdrantVectorStore:
    def __init__(
        self,
        *,
        url: str,
        api_key: str | None = None,
        client: QdrantClient | None = None,
    ) -> None:
        self._client = client or QdrantClient(
            url=url,
            api_key=api_key,
            check_compatibility=False,
        )

    def ensure_collection(self, collection_name: str, *, vector_size: int) -> None:
        if self._client.collection_exists(collection_name):
            info = self._client.get_collection(collection_name)
            existing_size = info.config.params.vectors.size  # type: ignore[union-attr]
            if existing_size != vector_size:
                raise ValueError(
                    f"Collection {collection_name} uses vector size {existing_size}, "
                    f"expected {vector_size}. Use a new collection or re-index."
                )
            return

        self._client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        logger.info(
            "created Qdrant collection %s (dim=%s)", collection_name, vector_size
        )

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

    def search(
        self,
        collection_name: str,
        *,
        query_vector: list[float],
        limit: int,
        source_uri: str | None = None,
    ) -> list[RagSearchHit]:
        query_filter = None
        if source_uri:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="source_uri",
                        match=MatchValue(value=source_uri),
                    )
                ]
            )

        if not self._client.collection_exists(collection_name):
            return []

        response = self._client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
        )

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
