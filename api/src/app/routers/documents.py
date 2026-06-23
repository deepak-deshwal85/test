from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.dependencies import get_document_service, verify_api_key
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
    dependencies=[Depends(verify_api_key)],
)


@router.post("", response_model=DocumentUploadResponse)
async def upload_document(
    collection: str,
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    filename = file.filename or "upload.txt"
    try:
        result = service.ingest_upload(
            collection=collection,
            filename=filename,
            content=content,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return DocumentUploadResponse(
        collection=result.collection,
        document_id=result.document_id,
        source_uri=result.source_uri,
        chunks_indexed=result.chunks_indexed,
    )


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document_alias(
    collection: str,
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    return await upload_document(collection=collection, file=file, service=service)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    collection: str,
    service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentListResponse:
    documents = service.list_documents(collection)
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
) -> DocumentDeleteResponse:
    try:
        service.delete_document(collection, document_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DocumentDeleteResponse(status="deleted", document_id=document_id)
