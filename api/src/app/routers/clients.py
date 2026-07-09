from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_client_repository, get_client_service, verify_access_token
from app.core.oauth import AuthenticatedPrincipal
from app.core.tenant import is_scope_unrestricted, principal_email, verify_client_email_scope
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
    email = principal_email(principal)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authenticated user email is required",
        )
    return await service.ensure_on_sign_in(
        client_email_id=email,
        cognito_sub=principal.subject,
    )


@router.get("/profile", response_model=ClientProfileResponse)
async def get_client_profile(
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    service: Annotated[ClientService, Depends(get_client_service)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
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
    scoped_email = await verify_client_email_scope(
        principal, resolved_email, repository
    )
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
    token_email = principal_email(principal)
    if not token_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authenticated user email is required",
        )
    if not is_scope_unrestricted(principal):
        await verify_client_email_scope(principal, token_email, repository)
    try:
        return await service.upsert_profile(
            body,
            client_email_id=token_email,
            cognito_sub=principal.subject,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
