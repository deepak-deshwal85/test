from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from app.core.dependencies import (
    get_call_job_service,
    get_client_repository,
    get_voice_agent_schedule_service,
    require_permission,
    verify_access_token,
)
from app.core.oauth import AuthenticatedPrincipal
from app.core.rbac import Permission
from app.core.tenant import verify_client_email_scope
from app.db.postgres.client_repository import ClientRepository
from app.schemas.voice_agent_schedules import (
    VoiceAgentScheduleOverviewResponse,
    VoiceAgentScheduleTriggerResponse,
    VoiceAgentScheduleUpdateRequest,
)
from app.services.call_job_service import CallJobService
from app.services.voice_agent_schedule_service import VoiceAgentScheduleService

router = APIRouter(
    prefix="/v1/voice-agent-schedule",
    tags=["voice-agent-schedule"],
    dependencies=[Depends(verify_access_token)],
)


@router.get("", response_model=VoiceAgentScheduleOverviewResponse)
async def get_voice_agent_schedule(
    client_email_id: Annotated[str, Query(min_length=3)],
    service: Annotated[
        VoiceAgentScheduleService, Depends(get_voice_agent_schedule_service)
    ],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
) -> VoiceAgentScheduleOverviewResponse:
    scoped_email = await verify_client_email_scope(
        principal, client_email_id, repository
    )
    try:
        return await service.get_overview(client_email_id=scoped_email)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("", response_model=VoiceAgentScheduleOverviewResponse)
async def update_voice_agent_schedule(
    body: VoiceAgentScheduleUpdateRequest,
    client_email_id: Annotated[str, Query(min_length=3)],
    service: Annotated[
        VoiceAgentScheduleService, Depends(get_voice_agent_schedule_service)
    ],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(require_permission(Permission.DOCUMENT_WRITE)),
    ],
) -> VoiceAgentScheduleOverviewResponse:
    scoped_email = await verify_client_email_scope(
        principal, client_email_id, repository
    )
    try:
        return await service.update(client_email_id=scoped_email, body=body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/trigger",
    response_model=VoiceAgentScheduleTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Run scheduled campaign now",
)
async def trigger_voice_agent_schedule(
    client_email_id: Annotated[str, Query(min_length=3)],
    background_tasks: BackgroundTasks,
    service: Annotated[
        VoiceAgentScheduleService, Depends(get_voice_agent_schedule_service)
    ],
    call_job_service: Annotated[CallJobService, Depends(get_call_job_service)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(require_permission(Permission.DOCUMENT_WRITE)),
    ],
) -> VoiceAgentScheduleTriggerResponse:
    scoped_email = await verify_client_email_scope(
        principal, client_email_id, repository
    )
    try:
        result = await service.trigger_now(
            client_email_id=scoped_email,
            run_job=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    background_tasks.add_task(call_job_service.run_job, result.job_id)
    return result
