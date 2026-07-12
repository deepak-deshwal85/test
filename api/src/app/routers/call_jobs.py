from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from app.core.dependencies import (
    get_call_job_service,
    get_client_repository,
    require_permission,
    verify_access_token,
)
from app.core.oauth import AuthenticatedPrincipal
from app.core.rbac import Permission
from app.core.tenant import is_scope_unrestricted, verify_client_email_scope
from app.db.postgres.client_repository import ClientRepository
from app.schemas.call_jobs import (
    CallJobListResponse,
    CallJobResponse,
    TriggerCallJobRequest,
    TriggerCallJobResponse,
)
from app.services.call_job_service import CallJobService

router = APIRouter(
    prefix="/v1/call-jobs",
    tags=["call-jobs"],
    dependencies=[Depends(verify_access_token)],
)


async def _resolve_client_id(
    principal: AuthenticatedPrincipal,
    client_email_id: str | None,
    repository: ClientRepository,
) -> int | None:
    if is_scope_unrestricted(principal):
        if not client_email_id:
            return None
        client = await repository.get_by_email(client_email_id.strip().lower())
        return client.id if client else None
    if not client_email_id:
        raise HTTPException(status_code=400, detail="client_email_id is required")
    scoped_email = await verify_client_email_scope(principal, client_email_id, repository)
    client = await repository.get_by_email(scoped_email)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return client.id


@router.post(
    "/trigger",
    response_model=TriggerCallJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger outbound campaign",
)
async def trigger_call_job(
    body: TriggerCallJobRequest,
    background_tasks: BackgroundTasks,
    service: Annotated[CallJobService, Depends(get_call_job_service)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(require_permission(Permission.DOCUMENT_WRITE)),
    ],
) -> TriggerCallJobResponse:
    scoped_email = await verify_client_email_scope(
        principal, body.client_email_id, repository
    )
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
    try:
        job = await service.create_job(client.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    background_tasks.add_task(service.run_job, job.id)
    return TriggerCallJobResponse(
        job_id=job.id,
        status=job.status,
        message=(
            f"Campaign queued for client {client.client_business_phone_number}. "
            f"Poll GET /v1/call-jobs/{job.id} for status."
        ),
    )


@router.get("", response_model=CallJobListResponse)
async def list_call_jobs(
    service: Annotated[CallJobService, Depends(get_call_job_service)],
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    client_email_id: Annotated[str | None, Query(min_length=3)] = None,
    limit: int = 20,
) -> CallJobListResponse:
    client_id = await _resolve_client_id(principal, client_email_id, repository)
    jobs = await service.list_jobs(
        client_id=client_id,
        limit=min(max(limit, 1), 100),
    )
    return CallJobListResponse(jobs=jobs, count=len(jobs))


@router.get("/{job_id}", response_model=CallJobResponse)
async def get_call_job(
    job_id: UUID,
    service: Annotated[CallJobService, Depends(get_call_job_service)],
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    client_email_id: Annotated[str | None, Query(min_length=3)] = None,
) -> CallJobResponse:
    client_id = await _resolve_client_id(principal, client_email_id, repository)
    job = await service.get_job(job_id, client_id=client_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Call job not found")
    return job
