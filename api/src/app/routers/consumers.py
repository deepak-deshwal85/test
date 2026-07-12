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
from app.core.tenant import is_scope_unrestricted, principal_email, verify_client_email_scope
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


async def _validate_consumer_write_scope(
    principal: AuthenticatedPrincipal,
    body_email: str,
    body_business_phone: str | None,
    repository: ClientRepository,
) -> str:
    scoped_email = await verify_client_email_scope(principal, body_email, repository)
    if is_scope_unrestricted(principal):
        return scoped_email

    client = await repository.get_by_email(scoped_email)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client profile not found",
        )
    if not client.client_business_phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Client business phone number is not configured",
        )
    if (
        body_business_phone
        and body_business_phone != client.client_business_phone_number
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client business phone number cannot be changed",
        )
    return scoped_email


@router.post("", response_model=ConsumerResponse, status_code=status.HTTP_201_CREATED)
async def create_consumer(
    body: ConsumerCreateRequest,
    service: Annotated[ConsumerService, Depends(get_consumer_service)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(require_permission(Permission.DOCUMENT_WRITE)),
    ],
) -> ConsumerResponse:
    scoped_email = await _validate_consumer_write_scope(
        principal,
        body.client_email_id,
        body.client_business_phone_number,
        repository,
    )
    if not is_scope_unrestricted(principal):
        client = await repository.get_by_email(scoped_email)
        if client is None:
            raise HTTPException(status_code=404, detail="Client profile not found")
        body = body.model_copy(
            update={
                "client_email_id": client.client_email_id,
                "client_business_phone_number": client.client_business_phone_number,
                "client_name": client.client_name or body.client_name,
            }
        )
    try:
        return await service.create(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=ConsumerListResponse)
async def list_consumers(
    service: Annotated[ConsumerService, Depends(get_consumer_service)],
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    client_email_id: Annotated[str | None, Query(min_length=3)] = None,
    client_business_phone_number: Annotated[str | None, Query()] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> ConsumerListResponse:
    if not client_email_id and not is_scope_unrestricted(principal):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_email_id is required",
        )
    scoped_email = (
        await verify_client_email_scope(principal, client_email_id, repository)
        if client_email_id
        else None
    )
    consumers = await service.list(
        client_email_id=scoped_email,
        client_business_phone_number=client_business_phone_number,
        skip=skip,
        limit=limit,
    )
    return ConsumerListResponse(consumers=consumers, count=len(consumers))


@router.get("/{consumer_id}", response_model=ConsumerResponse)
async def get_consumer(
    consumer_id: int,
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    client_email_id: Annotated[str, Query(min_length=3)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    service: Annotated[ConsumerService, Depends(get_consumer_service)],
) -> ConsumerResponse:
    scoped_email = await verify_client_email_scope(
        principal, client_email_id, repository
    )
    consumer = await service.get(consumer_id, client_email_id=scoped_email)
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
    scoped_email = await _validate_consumer_write_scope(
        principal,
        client_email_id,
        body.client_business_phone_number,
        repository,
    )
    if not is_scope_unrestricted(principal):
        body = body.model_copy(
            update={
                "client_business_phone_number": None,
                "client_email_id": None,
            }
        )
    try:
        consumer = await service.update(
            consumer_id,
            client_email_id=scoped_email,
            body=body,
        )
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
    scoped_email = await verify_client_email_scope(
        principal, client_email_id, repository
    )
    deleted = await service.delete(consumer_id, client_email_id=scoped_email)
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
    _principal: Annotated[object, Depends(require_permission(Permission.ADMIN))] = ...,
) -> ConsumerResponse:
    consumer = await service.approve(consumer_id, client_email_id=client_email_id)
    if consumer is None:
        raise HTTPException(status_code=404, detail="Consumer not found")
    return consumer
