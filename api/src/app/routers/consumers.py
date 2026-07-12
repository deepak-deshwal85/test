from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import (
    get_client_repository,
    get_consumer_service,
    require_permission,
    verify_access_token,
)
from app.core.oauth import AuthenticatedPrincipal
from app.core.rbac import Permission
from app.core.tenant import is_scope_unrestricted, verify_client_email_scope
from app.db.postgres.client_repository import ClientRepository
from app.schemas.consumers import (
    ConsumerCreateRequest,
    ConsumerListResponse,
    ConsumerResponse,
    ConsumerUpdateRequest,
)
from app.services.consumer_service import ConsumerService

router = APIRouter(
    prefix="/v1/consumers",
    tags=["consumers"],
    dependencies=[Depends(verify_access_token)],
)


async def _resolve_client(
    principal: AuthenticatedPrincipal,
    client_email_id: str,
    repository: ClientRepository,
):
    """Resolve and scope-check the email, then return the full Client row."""
    scoped_email = await verify_client_email_scope(principal, client_email_id, repository)
    client = await repository.get_by_email(scoped_email)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client profile not found",
        )
    return client


@router.post("", response_model=ConsumerResponse, status_code=status.HTTP_201_CREATED)
async def create_consumer(
    body: ConsumerCreateRequest,
    client_email_id: Annotated[str, Query(min_length=3)],
    service: Annotated[ConsumerService, Depends(get_consumer_service)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(require_permission(Permission.DOCUMENT_WRITE)),
    ],
) -> ConsumerResponse:
    client = await _resolve_client(principal, client_email_id, repository)
    if not client.client_business_phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client business phone number is not configured",
        )
    try:
        return await service.create(client, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=ConsumerListResponse)
async def list_consumers(
    service: Annotated[ConsumerService, Depends(get_consumer_service)],
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    client_email_id: Annotated[str | None, Query(min_length=3)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> ConsumerListResponse:
    if not client_email_id and not is_scope_unrestricted(principal):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_email_id is required",
        )
    client_id: int | None = None
    if client_email_id:
        client = await _resolve_client(principal, client_email_id, repository)
        client_id = client.id
    consumers = await service.list(client_id=client_id, skip=skip, limit=limit)
    return ConsumerListResponse(consumers=consumers, count=len(consumers))


@router.get("/{consumer_id}", response_model=ConsumerResponse)
async def get_consumer(
    consumer_id: int,
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    client_email_id: Annotated[str, Query(min_length=3)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    service: Annotated[ConsumerService, Depends(get_consumer_service)],
) -> ConsumerResponse:
    client = await _resolve_client(principal, client_email_id, repository)
    consumer = await service.get(consumer_id, client_id=client.id)
    if consumer is None:
        raise HTTPException(status_code=404, detail="Consumer not found")
    return consumer


@router.put("/{consumer_id}", response_model=ConsumerResponse)
async def update_consumer(
    consumer_id: int,
    client_email_id: Annotated[str, Query(min_length=3)],
    body: ConsumerUpdateRequest,
    service: Annotated[ConsumerService, Depends(get_consumer_service)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(require_permission(Permission.DOCUMENT_WRITE)),
    ],
) -> ConsumerResponse:
    client = await _resolve_client(principal, client_email_id, repository)
    try:
        consumer = await service.update(consumer_id, client_id=client.id, body=body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if consumer is None:
        raise HTTPException(status_code=404, detail="Consumer not found")
    return consumer


@router.delete("/{consumer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_consumer(
    consumer_id: int,
    client_email_id: Annotated[str, Query(min_length=3)],
    service: Annotated[ConsumerService, Depends(get_consumer_service)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(require_permission(Permission.DOCUMENT_WRITE)),
    ],
) -> None:
    client = await _resolve_client(principal, client_email_id, repository)
    deleted = await service.delete(consumer_id, client_id=client.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Consumer not found")


@router.post(
    "/{consumer_id}/approve",
    response_model=ConsumerResponse,
    status_code=status.HTTP_200_OK,
)
async def approve_consumer(
    consumer_id: int,
    client_email_id: Annotated[str, Query(min_length=3)],
    service: Annotated[ConsumerService, Depends(get_consumer_service)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    _principal: Annotated[object, Depends(require_permission(Permission.ADMIN))] = ...,
) -> ConsumerResponse:
    client = await repository.get_by_email(client_email_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    consumer = await service.approve(consumer_id, client_id=client.id)
    if consumer is None:
        raise HTTPException(status_code=404, detail="Consumer not found")
    return consumer
