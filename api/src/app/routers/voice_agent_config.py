from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import (
    get_client_repository,
    get_client_voice_agent_config_service,
    require_permission,
    verify_access_token,
)
from app.core.oauth import AuthenticatedPrincipal
from app.core.rbac import Permission
from app.core.tenant import verify_client_email_scope
from app.db.postgres.client_repository import ClientRepository
from app.schemas.voice_agent_config import (
    VoiceAgentConfigResolveResponse,
    VoiceAgentConfigResponse,
    VoiceAgentConfigUpdateRequest,
)
from app.services.client_voice_agent_config_service import ClientVoiceAgentConfigService

router = APIRouter(
    prefix="/v1/voice-agent-config",
    tags=["voice-agent-config"],
    dependencies=[Depends(verify_access_token)],
)


@router.get("", response_model=VoiceAgentConfigResponse)
async def get_voice_agent_config(
    client_email_id: Annotated[str, Query(min_length=3)],
    service: Annotated[
        ClientVoiceAgentConfigService, Depends(get_client_voice_agent_config_service)
    ],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
) -> VoiceAgentConfigResponse:
    scoped_email = await verify_client_email_scope(
        principal, client_email_id, repository
    )
    try:
        return await service.get(client_email_id=scoped_email)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("", response_model=VoiceAgentConfigResponse)
async def update_voice_agent_config(
    body: VoiceAgentConfigUpdateRequest,
    client_email_id: Annotated[str, Query(min_length=3)],
    service: Annotated[
        ClientVoiceAgentConfigService, Depends(get_client_voice_agent_config_service)
    ],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(require_permission(Permission.DOCUMENT_WRITE)),
    ],
) -> VoiceAgentConfigResponse:
    scoped_email = await verify_client_email_scope(
        principal, client_email_id, repository
    )
    try:
        return await service.update(client_email_id=scoped_email, body=body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/resolve-by-phone", response_model=VoiceAgentConfigResolveResponse)
async def resolve_voice_agent_config_by_phone(
    phone_number: Annotated[str, Query(min_length=5, max_length=32)],
    service: Annotated[
        ClientVoiceAgentConfigService, Depends(get_client_voice_agent_config_service)
    ],
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
) -> VoiceAgentConfigResolveResponse:
    if not principal.is_m2m:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Voice agent config resolution is available to machine clients only",
        )

    resolved = await service.resolve_by_phone(phone_number)
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No voice agent config found for this business phone number",
        )
    return resolved


@router.get("/resolve-by-email", response_model=VoiceAgentConfigResolveResponse)
async def resolve_voice_agent_config_by_email(
    client_email_id: Annotated[str, Query(min_length=3)],
    service: Annotated[
        ClientVoiceAgentConfigService, Depends(get_client_voice_agent_config_service)
    ],
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
) -> VoiceAgentConfigResolveResponse:
    if not principal.is_m2m:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Voice agent config resolution is available to machine clients only",
        )

    resolved = await service.resolve_by_email(client_email_id)
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No voice agent config found for this client email",
        )
    return resolved
