from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import (
    get_embedding_service,
    require_permission,
    verify_access_token,
)
from app.core.rbac import Permission
from app.schemas.embeddings import (
    EmbeddingCacheDeleteResponse,
    EmbeddingCacheStatsResponse,
    EmbeddingLookupResponse,
    EmbedRequest,
    EmbedResponse,
)
from app.services.embedding_service import EmbeddingService

router = APIRouter(
    prefix="/v1/embeddings",
    tags=["embeddings"],
    dependencies=[Depends(verify_access_token)],
)


@router.post("", response_model=EmbedResponse)
def create_embeddings(
    body: EmbedRequest,
    service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    _principal: Annotated[object, Depends(require_permission(Permission.ADMIN))] = ...,
) -> EmbedResponse:
    try:
        result = service.create_embeddings(body.texts)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return EmbedResponse(
        model=result.model,
        dimensions=result.dimensions,
        embeddings=result.embeddings,
        cache_hits=result.cache_hits,
        cache_misses=result.cache_misses,
    )


@router.get("/cache", response_model=EmbeddingCacheStatsResponse)
def get_cache_stats(
    service: Annotated[EmbeddingService, Depends(get_embedding_service)],
) -> EmbeddingCacheStatsResponse:
    stats = service.cache_stats()
    return EmbeddingCacheStatsResponse(
        enabled=bool(stats["enabled"]),
        count=int(stats["count"]),
    )


@router.get("/cache/lookup", response_model=EmbeddingLookupResponse)
def lookup_cached_embedding(
    text: Annotated[str, Query(min_length=1)],
    service: Annotated[EmbeddingService, Depends(get_embedding_service)],
) -> EmbeddingLookupResponse:
    embedding = service.lookup_cached(text)
    return EmbeddingLookupResponse(
        text=text,
        cached=embedding is not None,
        embedding=embedding,
    )


@router.delete("/cache", response_model=EmbeddingCacheDeleteResponse)
def clear_embedding_cache(
    service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    _principal: Annotated[object, Depends(require_permission(Permission.ADMIN))] = ...,
) -> EmbeddingCacheDeleteResponse:
    cleared = service.clear_cache()
    return EmbeddingCacheDeleteResponse(deleted=cleared > 0, cleared_count=cleared)


@router.delete("/cache/entry", response_model=EmbeddingCacheDeleteResponse)
def delete_cached_embedding(
    text: Annotated[str, Query(min_length=1)],
    service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    _principal: Annotated[object, Depends(require_permission(Permission.ADMIN))] = ...,
) -> EmbeddingCacheDeleteResponse:
    deleted = service.delete_cached(text)
    return EmbeddingCacheDeleteResponse(deleted=deleted)
