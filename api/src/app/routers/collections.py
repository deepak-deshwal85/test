from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.core.dependencies import get_collection_service, verify_api_key
from app.core.qdrant_errors import is_qdrant_connection_error, qdrant_unavailable_detail
from app.schemas.collections import (
    CollectionDeleteResponse,
    CollectionInfoResponse,
    CollectionListResponse,
)
from app.services.collection_service import CollectionService

router = APIRouter(
    prefix="/v1/collections",
    tags=["collections"],
    dependencies=[Depends(verify_api_key)],
)


@router.get("", response_model=CollectionListResponse)
def list_collections(
    service: Annotated[CollectionService, Depends(get_collection_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CollectionListResponse:
    try:
        collections = service.list_collections()
    except Exception as exc:
        if is_qdrant_connection_error(exc):
            raise HTTPException(
                status_code=503, detail=qdrant_unavailable_detail(settings)
            ) from exc
        raise
    return CollectionListResponse(collections=collections, count=len(collections))


@router.get("/{collection}", response_model=CollectionInfoResponse)
def get_collection(
    collection: str,
    service: Annotated[CollectionService, Depends(get_collection_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CollectionInfoResponse:
    try:
        info = service.get_collection(collection)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        if is_qdrant_connection_error(exc):
            raise HTTPException(
                status_code=503, detail=qdrant_unavailable_detail(settings)
            ) from exc
        raise
    return CollectionInfoResponse(
        name=str(info["name"]),
        points_count=int(info["points_count"]),
        vector_size=int(info["vector_size"]),
    )


@router.delete("/{collection}", response_model=CollectionDeleteResponse)
def delete_collection(
    collection: str,
    service: Annotated[CollectionService, Depends(get_collection_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CollectionDeleteResponse:
    try:
        service.delete_collection(collection)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        if is_qdrant_connection_error(exc):
            raise HTTPException(
                status_code=503, detail=qdrant_unavailable_detail(settings)
            ) from exc
        raise
    return CollectionDeleteResponse(status="deleted", collection=collection)
