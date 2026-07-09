from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_client_service, verify_access_token
from app.core.oauth import AuthenticatedPrincipal
from app.core.tenant import ensure_client_email_scope, is_scope_unrestricted
from app.schemas.clients import ClientProfileResponse, ClientProfileUpsertRequest
from app.services.client_service import ClientService

router = APIRouter(
    prefix="/v1/clients",
    tags=["clients"],
    dependencies=[Depends(verify_access_token)],
)


@router.get("/profile", response_model=ClientProfileResponse)
async def get_client_profile(
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    service: Annotated[ClientService, Depends(get_client_service)],
    client_email_id: Annotated[str, Query(min_length=3)],
) -> ClientProfileResponse:
    if principal.is_m2m:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client profile is not available for machine clients",
        )
    scoped_email = ensure_client_email_scope(principal, client_email_id)
    profile = await service.get_profile(scoped_email)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client profile not found",
        )
    return profile


@router.put("/profile", response_model=ClientProfileResponse)
async def upsert_client_profile(
    body: ClientProfileUpsertRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    service: Annotated[ClientService, Depends(get_client_service)],
) -> ClientProfileResponse:
    if principal.is_m2m:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client profile is not available for machine clients",
        )
    if not is_scope_unrestricted(principal):
        ensure_client_email_scope(principal, body.client_email_id)
    try:
        return await service.upsert_profile(
            body,
            cognito_sub=principal.subject,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
