from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from app.core.dependencies import get_call_job_service, verify_api_key
from app.schemas.call_jobs import (
    CallJobResponse,
    TriggerCallJobRequest,
    TriggerCallJobResponse,
)
from app.services.call_job_service import CallJobService

router = APIRouter(
    prefix="/v1/call-jobs",
    tags=["call-jobs"],
    dependencies=[Depends(verify_api_key)],
)


@router.post(
    "/trigger",
    response_model=TriggerCallJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_call_job(
    body: TriggerCallJobRequest,
    background_tasks: BackgroundTasks,
    service: Annotated[CallJobService, Depends(get_call_job_service)],
) -> TriggerCallJobResponse:
    job = await service.create_job(body.client_phone_number)
    background_tasks.add_task(service.run_job, job.id)
    return TriggerCallJobResponse(
        job_id=job.id,
        status=job.status,
        message=(
            f"Call job queued for client {job.client_phone_number}. "
            f"Poll GET /v1/call-jobs/{job.id} for status."
        ),
    )


@router.get("/{job_id}", response_model=CallJobResponse)
async def get_call_job(
    job_id: UUID,
    service: Annotated[CallJobService, Depends(get_call_job_service)],
) -> CallJobResponse:
    job = await service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Call job not found")
    return job
