from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import (
    get_call_summary_service,
    get_client_repository,
    get_consumer_service,
    require_permission,
    verify_access_token,
)
from app.core.oauth import AuthenticatedPrincipal
from app.core.rbac import Permission
from app.core.tenant import is_scope_unrestricted, verify_client_email_scope
from app.db.postgres.client_repository import ClientRepository
from app.schemas.call_summaries import (
    CallSummaryCreateRequest,
    CallSummaryListResponse,
    CallSummaryResponse,
    CallSummaryUpdateRequest,
)
from app.services.call_summary_service import CallSummaryService
from app.services.consumer_service import ConsumerService

router = APIRouter(
    prefix="/v1/call-summaries",
    tags=["call-summaries"],
    dependencies=[Depends(verify_access_token)],
)


async def _resolve_client_email_for_create(
    *,
    principal: AuthenticatedPrincipal,
    body: CallSummaryCreateRequest,
    consumer_service: ConsumerService,
    repository: ClientRepository,
    client_email_id: str | None,
) -> str:
    if principal.is_m2m:
        consumer = await consumer_service.get_by_id(body.consumer_id)
        if consumer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Consumer not found",
            )
        if client_email_id:
            scoped = await verify_client_email_scope(
                principal, client_email_id, repository
            )
            if consumer.client_email_id != scoped:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Consumer not found",
                )
        return consumer.client_email_id

    if not client_email_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_email_id is required",
        )
    consumer = await consumer_service.get(
        body.consumer_id, client_email_id=client_email_id
    )
    if consumer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consumer not found",
        )
    return await verify_client_email_scope(principal, client_email_id, repository)


@router.post(
    "", response_model=CallSummaryResponse, status_code=status.HTTP_201_CREATED
)
async def create_call_summary(
    body: CallSummaryCreateRequest,
    service: Annotated[CallSummaryService, Depends(get_call_summary_service)],
    consumer_service: Annotated[ConsumerService, Depends(get_consumer_service)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    client_email_id: Annotated[str | None, Query(min_length=3)] = None,
) -> CallSummaryResponse:
    if not principal.is_m2m and not principal.has_permission(Permission.DOCUMENT_WRITE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

    scoped_email = await _resolve_client_email_for_create(
        principal=principal,
        body=body,
        consumer_service=consumer_service,
        repository=repository,
        client_email_id=client_email_id,
    )

    try:
        return await service.create(client_email_id=scoped_email, body=body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=CallSummaryListResponse)
async def list_call_summaries(
    service: Annotated[CallSummaryService, Depends(get_call_summary_service)],
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    client_email_id: Annotated[str | None, Query(min_length=3)] = None,
    consumer_id: Annotated[int | None, Query(ge=1)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> CallSummaryListResponse:
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
    summaries = await service.list(
        client_email_id=scoped_email,
        consumer_id=consumer_id,
        skip=skip,
        limit=limit,
    )
    return CallSummaryListResponse(summaries=summaries, count=len(summaries))


@router.get("/{summary_id}", response_model=CallSummaryResponse)
async def get_call_summary(
    summary_id: int,
    client_email_id: Annotated[str, Query(min_length=3)],
    service: Annotated[CallSummaryService, Depends(get_call_summary_service)],
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
) -> CallSummaryResponse:
    scoped_email = await verify_client_email_scope(
        principal, client_email_id, repository
    )
    summary = await service.get(summary_id, client_email_id=scoped_email)
    if summary is None:
        raise HTTPException(status_code=404, detail="Call summary not found")
    return summary


@router.put("/{summary_id}", response_model=CallSummaryResponse)
async def update_call_summary(
    summary_id: int,
    client_email_id: Annotated[str, Query(min_length=3)],
    body: CallSummaryUpdateRequest,
    service: Annotated[CallSummaryService, Depends(get_call_summary_service)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(require_permission(Permission.DOCUMENT_WRITE)),
    ],
) -> CallSummaryResponse:
    scoped_email = await verify_client_email_scope(
        principal, client_email_id, repository
    )
    summary = await service.update(summary_id, client_email_id=scoped_email, body=body)
    if summary is None:
        raise HTTPException(status_code=404, detail="Call summary not found")
    return summary


@router.delete("/{summary_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_call_summary(
    summary_id: int,
    client_email_id: Annotated[str, Query(min_length=3)],
    service: Annotated[CallSummaryService, Depends(get_call_summary_service)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(require_permission(Permission.DOCUMENT_WRITE)),
    ],
) -> None:
    scoped_email = await verify_client_email_scope(
        principal, client_email_id, repository
    )
    deleted = await service.delete(summary_id, client_email_id=scoped_email)
    if not deleted:
        raise HTTPException(status_code=404, detail="Call summary not found")
