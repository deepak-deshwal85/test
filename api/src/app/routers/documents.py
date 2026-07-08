from __future__ import annotations

import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.config import Settings, get_settings
from app.core.dependencies import get_document_service, verify_access_token
from app.core.qdrant_errors import is_qdrant_connection_error, qdrant_unavailable_detail
from app.schemas.documents import (
    DocumentDeleteResponse,
    DocumentListResponse,
    DocumentSummaryResponse,
    DocumentUploadResponse,
)
from app.services.document_service import DocumentService

router = APIRouter(
    prefix="/v1/collections/{collection}/documents",
    tags=["documents"],
    dependencies=[Depends(verify_access_token)],
)


@router.post("", response_model=DocumentUploadResponse)
@router.post("/upload", response_model=DocumentUploadResponse)
def upload_document(
    collection: str,
    file: UploadFile = File(...),
    service: Annotated[DocumentService, Depends(get_document_service)] = ...,
    settings: Annotated[Settings, Depends(get_settings)] = ...,
) -> DocumentUploadResponse:
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    filename = file.filename or "upload.txt"
    started = time.perf_counter()
    try:
        result = service.ingest_upload(
            collection=collection,
            filename=filename,
            content=content,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        if is_qdrant_connection_error(exc):
            raise HTTPException(
                status_code=503, detail=qdrant_unavailable_detail(settings)
            ) from exc
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    logging.getLogger("relaydesk-api").info(
        "POST /v1/collections/%s/documents file=%r chunks=%d total_ms=%.0f",
        collection,
        filename,
        result.chunks_indexed,
        (time.perf_counter() - started) * 1000,
    )
    return DocumentUploadResponse(
        collection=result.collection,
        document_id=result.document_id,
        source_uri=result.source_uri,
        chunks_indexed=result.chunks_indexed,
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    collection: str,
    service: Annotated[DocumentService, Depends(get_document_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentListResponse:
    try:
        documents = service.list_documents(collection)
    except Exception as exc:
        if is_qdrant_connection_error(exc):
            raise HTTPException(
                status_code=503, detail=qdrant_unavailable_detail(settings)
            ) from exc
        raise
    summaries = [
        DocumentSummaryResponse(
            document_id=doc.document_id,
            source_uri=doc.source_uri,
            chunk_count=doc.chunk_count,
        )
        for doc in documents
    ]
    return DocumentListResponse(
        collection=collection,
        documents=summaries,
        count=len(summaries),
    )


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
def delete_document(
    collection: str,
    document_id: str,
    service: Annotated[DocumentService, Depends(get_document_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentDeleteResponse:
    try:
        service.delete_document(collection, document_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        if is_qdrant_connection_error(exc):
            raise HTTPException(
                status_code=503, detail=qdrant_unavailable_detail(settings)
            ) from exc
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DocumentDeleteResponse(status="deleted", document_id=document_id)
