from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import Settings, get_settings
from app.core.dependencies import (
    get_client_repository,
    get_collection_service,
    require_permission,
    verify_access_token,
)
from app.core.oauth import AuthenticatedPrincipal
from app.core.rbac import Permission
from app.core.qdrant_errors import is_qdrant_connection_error, qdrant_unavailable_detail
from app.core.tenant import (
    ensure_collection_access,
    filter_collections,
    is_scope_unrestricted,
    resolve_client_scope,
    verify_client_email_scope,
)
from app.db.postgres.client_repository import ClientRepository
from app.schemas.collections import (
    CollectionDeleteResponse,
    CollectionInfoResponse,
    CollectionListResponse,
)
from app.services.collection_service import CollectionService

router = APIRouter(
    prefix="/v1/collections",
    tags=["collections"],
    dependencies=[Depends(verify_access_token)],
)


async def _load_scope(
    principal: AuthenticatedPrincipal,
    client_email_id: str | None,
    repository: ClientRepository,
):
    if is_scope_unrestricted(principal) and not client_email_id:
        return resolve_client_scope(
            principal,
            client_email_id=None,
            client=None,
        )
    client = None
    if client_email_id:
        await verify_client_email_scope(principal, client_email_id, repository)
        client = await repository.get_by_email(client_email_id)
    return resolve_client_scope(
        principal,
        client_email_id=client_email_id,
        client=client,
    )


@router.get("", response_model=CollectionListResponse)
async def list_collections(
    service: Annotated[CollectionService, Depends(get_collection_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    client_email_id: Annotated[str | None, Query(min_length=3)] = None,
) -> CollectionListResponse:
    scope = await _load_scope(principal, client_email_id, repository)
    try:
        collections = service.list_collections()
    except Exception as exc:
        if is_qdrant_connection_error(exc):
            raise HTTPException(
                status_code=503, detail=qdrant_unavailable_detail(settings)
            ) from exc
        raise
    filtered = filter_collections(scope, collections)
    return CollectionListResponse(
        collections=filtered,
        count=len(filtered),
        client_business_phone_number=scope.client_business_phone_number,
        client_email_id=scope.client_email_id,
    )


@router.get("/{collection}", response_model=CollectionInfoResponse)
async def get_collection(
    collection: str,
    service: Annotated[CollectionService, Depends(get_collection_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    client_email_id: Annotated[str | None, Query(min_length=3)] = None,
) -> CollectionInfoResponse:
    scope = await _load_scope(principal, client_email_id, repository)
    ensure_collection_access(scope, collection)
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
        client_business_phone_number=scope.client_business_phone_number,
    )


@router.delete("/{collection}", response_model=CollectionDeleteResponse)
async def delete_collection(
    collection: str,
    service: Annotated[CollectionService, Depends(get_collection_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    client_email_id: Annotated[str | None, Query(min_length=3)] = None,
    _admin: Annotated[object, Depends(require_permission(Permission.ADMIN))] = ...,
) -> CollectionDeleteResponse:
    scope = await _load_scope(principal, client_email_id, repository)
    ensure_collection_access(scope, collection)
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
