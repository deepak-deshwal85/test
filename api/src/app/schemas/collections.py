from __future__ import annotations

from pydantic import BaseModel


class CollectionInfoResponse(BaseModel):
    name: str
    points_count: int
    vector_size: int
    client_business_phone_number: str | None = None


class CollectionListResponse(BaseModel):
    collections: list[str]
    count: int
    client_business_phone_number: str | None = None
    client_email_id: str | None = None


class CollectionDeleteResponse(BaseModel):
    status: str
    collection: str
