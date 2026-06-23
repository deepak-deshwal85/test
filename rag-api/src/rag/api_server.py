from __future__ import annotations

import logging
import time
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from client_config import load_client_config, resolve_client_config
from rag.config import RagSettings, load_rag_settings, resolve_qdrant_collection
from rag.service import (
    embed_texts,
    hits_to_payload,
    ingest_uploaded_file,
    search_client_knowledge,
    search_collection,
)

logger = logging.getLogger("agent-telephone-agent")


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    max_results: int | None = Field(default=None, ge=1, le=20)
    collection: str | None = None
    phone_number: str | None = None


class EmbedRequest(BaseModel):
    texts: list[str] = Field(min_length=1)


def get_settings() -> RagSettings:
    return load_rag_settings()


def create_app() -> FastAPI:
    app = FastAPI(title="Telephone Agent RAG API", version="1.0.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/embeddings")
    def create_embeddings(
        body: EmbedRequest,
        settings: Annotated[RagSettings, Depends(get_settings)],
    ) -> dict[str, object]:
        try:
            result = embed_texts(body.texts, settings)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "model": result.model,
            "dimensions": result.dimensions,
            "embeddings": result.embeddings,
        }

    @app.post("/v1/collections/{collection}/documents")
    async def upload_document(
        collection: str,
        file: UploadFile = File(...),
        settings: RagSettings = Depends(get_settings),
    ) -> dict[str, object]:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        filename = file.filename or "upload.txt"
        try:
            result = ingest_uploaded_file(
                collection=collection,
                filename=filename,
                content=content,
                settings=settings,
            )
        except Exception as exc:
            logger.exception("document ingest failed")
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return {
            "collection": result.collection,
            "document_id": result.document_id,
            "source_uri": result.source_uri,
            "chunks_indexed": result.chunks_indexed,
        }

    @app.post("/v1/collections/{collection}/documents/upload")
    async def upload_document_alias(
        collection: str,
        file: UploadFile = File(...),
        settings: RagSettings = Depends(get_settings),
    ) -> dict[str, object]:
        return await upload_document(
            collection=collection, file=file, settings=settings
        )

    @app.delete("/v1/collections/{collection}/documents/{document_id}")
    def delete_document(
        collection: str,
        document_id: str,
        settings: RagSettings = Depends(get_settings),
    ) -> dict[str, str]:
        from rag.service import create_qdrant_store

        store = create_qdrant_store(settings)
        try:
            store.delete_document(collection, document_id)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"status": "deleted", "document_id": document_id}

    @app.post("/v1/search")
    def search(
        body: SearchRequest, settings: RagSettings = Depends(get_settings)
    ) -> dict[str, object]:
        max_results = body.max_results or settings.max_results
        started = time.perf_counter()
        try:
            if body.phone_number:
                client_config = resolve_client_config(
                    body.phone_number
                ) or load_client_config(body.phone_number)
                hits = search_client_knowledge(
                    client_config=client_config,
                    query=body.query,
                    max_results=max_results,
                    settings=settings,
                )
                collection = resolve_qdrant_collection(client_config, settings)
            elif body.collection:
                hits = search_collection(
                    collection=body.collection,
                    query=body.query,
                    max_results=max_results,
                    settings=settings,
                )
                collection = body.collection
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Provide either phone_number or collection",
                )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("search failed")
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        payload = hits_to_payload(hits)
        payload["collection"] = collection
        logger.info(
            "rag api /v1/search collection=%s hits=%d total_ms=%.0f query=%r",
            collection,
            len(hits),
            (time.perf_counter() - started) * 1000,
            body.query[:80],
        )
        return payload

    return app


app = create_app()
