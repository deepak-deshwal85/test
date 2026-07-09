from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from app.core.dependencies import (
    get_call_job_service,
    require_permission,
    verify_access_token,
)
from app.core.oauth import AuthenticatedPrincipal
from app.core.rbac import Permission
from app.core.tenant import ensure_client_email_scope, is_scope_unrestricted
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


def _scoped_email(
    principal: AuthenticatedPrincipal,
    client_email_id: str | None,
) -> str | None:
    if is_scope_unrestricted(principal):
        return client_email_id.strip().lower() if client_email_id else None
    if not client_email_id:
        raise HTTPException(status_code=400, detail="client_email_id is required")
    return ensure_client_email_scope(principal, client_email_id)


@router.post(
    "/trigger",
    response_model=TriggerCallJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_call_job(
    body: TriggerCallJobRequest,
    background_tasks: BackgroundTasks,
    service: Annotated[CallJobService, Depends(get_call_job_service)],
    _principal: Annotated[object, Depends(require_permission(Permission.ADMIN))] = ...,
) -> TriggerCallJobResponse:
    job = await service.create_job(body.client_phone_number, body.client_email_id)
    background_tasks.add_task(service.run_job, job.id)
    return TriggerCallJobResponse(
        job_id=job.id,
        status=job.status,
        message=(
            f"Call job queued for client {job.client_phone_number}. "
            f"Poll GET /v1/call-jobs/{job.id} for status."
        ),
    )


@router.get("", response_model=CallJobListResponse)
async def list_call_jobs(
    service: Annotated[CallJobService, Depends(get_call_job_service)],
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    client_email_id: Annotated[str | None, Query(min_length=3)] = None,
    client_phone_number: str | None = None,
    limit: int = 20,
) -> CallJobListResponse:
    scoped_email = _scoped_email(principal, client_email_id)
    jobs = await service.list_jobs(
        client_email_id=scoped_email,
        client_phone_number=client_phone_number,
        limit=min(max(limit, 1), 100),
    )
    return CallJobListResponse(jobs=jobs, count=len(jobs))


@router.get("/{job_id}", response_model=CallJobResponse)
async def get_call_job(
    job_id: UUID,
    service: Annotated[CallJobService, Depends(get_call_job_service)],
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    client_email_id: Annotated[str | None, Query(min_length=3)] = None,
) -> CallJobResponse:
    scoped_email = _scoped_email(principal, client_email_id)
    job = await service.get_job(job_id, client_email_id=scoped_email)
    if job is None:
        raise HTTPException(status_code=404, detail="Call job not found")
    return job
