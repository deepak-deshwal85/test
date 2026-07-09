from __future__ import annotations

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    collection: str
    document_id: str
    source_uri: str
    chunks_indexed: int
    client_business_phone_number: str | None = None


class DocumentSummaryResponse(BaseModel):
    document_id: str
    source_uri: str
    chunk_count: int


class DocumentListResponse(BaseModel):
    collection: str
    documents: list[DocumentSummaryResponse]
    count: int
    client_business_phone_number: str | None = None


class DocumentDeleteResponse(BaseModel):
    status: str
    document_id: str
