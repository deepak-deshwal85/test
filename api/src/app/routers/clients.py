from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_client_repository, get_client_service, verify_access_token
from app.core.oauth import AuthenticatedPrincipal
from app.core.tenant import ensure_client_email_scope, is_scope_unrestricted, principal_email
from app.db.postgres.client_repository import ClientRepository
from app.schemas.clients import ClientProfileResponse, ClientProfileUpsertRequest
from app.services.client_service import ClientService

router = APIRouter(
    prefix="/v1/clients",
    tags=["clients"],
    dependencies=[Depends(verify_access_token)],
)


@router.get("/me", response_model=ClientProfileResponse)
async def get_my_client_profile(
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    service: Annotated[ClientService, Depends(get_client_service)],
) -> ClientProfileResponse:
    if principal.is_m2m:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client profile is not available for machine clients",
        )
    profile = await service.get_profile_for_principal(
        cognito_sub=principal.subject,
        client_email_id=principal_email(principal),
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client profile not found",
        )
    return profile


@router.get("/profile", response_model=ClientProfileResponse)
async def get_client_profile(
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    service: Annotated[ClientService, Depends(get_client_service)],
    client_email_id: Annotated[str | None, Query(min_length=3)] = None,
) -> ClientProfileResponse:
    if principal.is_m2m:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client profile is not available for machine clients",
        )
    resolved_email = client_email_id or principal_email(principal)
    if not resolved_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_email_id is required",
        )
    scoped_email = ensure_client_email_scope(principal, resolved_email)
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
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
) -> ClientProfileResponse:
    if principal.is_m2m:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client profile is not available for machine clients",
        )
    if not is_scope_unrestricted(principal):
        normalized = body.client_email_id.strip().lower()
        token_email = principal_email(principal)
        if token_email and token_email != normalized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Client email scope mismatch",
            )
        existing = await repository.get_by_cognito_sub(principal.subject)
        if existing and existing.client_email_id != normalized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Client email scope mismatch",
            )
    try:
        return await service.upsert_profile(
            body,
            cognito_sub=principal.subject,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
