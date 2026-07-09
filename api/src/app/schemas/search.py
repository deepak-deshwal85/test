from __future__ import annotations

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    max_results: int | None = Field(default=None, ge=1, le=20)
    collection: str | None = None
    phone_number: str | None = None
    client_email_id: str | None = Field(default=None, min_length=3, max_length=255)


class SearchHitResponse(BaseModel):
    text: str
    score: float
    source_uri: str | None = None


class SearchResponse(BaseModel):
    hits: list[SearchHitResponse]
    count: int
    collection: str
    client_business_phone_number: str | None = None
    client_email_id: str | None = None
