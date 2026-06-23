from __future__ import annotations

from pydantic import BaseModel


class CollectionInfoResponse(BaseModel):
    name: str
    points_count: int
    vector_size: int


class CollectionListResponse(BaseModel):
    collections: list[str]
    count: int


class CollectionDeleteResponse(BaseModel):
    status: str
    collection: str
