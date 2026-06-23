from __future__ import annotations

from app.db.qdrant_repository import QdrantRepository


class CollectionService:
    def __init__(self, qdrant: QdrantRepository) -> None:
        self._qdrant = qdrant

    def list_collections(self) -> list[str]:
        return self._qdrant.list_collections()

    def get_collection(self, collection_name: str) -> dict[str, object]:
        return self._qdrant.get_collection(collection_name)

    def delete_collection(self, collection_name: str) -> None:
        self._qdrant.delete_collection(collection_name)
