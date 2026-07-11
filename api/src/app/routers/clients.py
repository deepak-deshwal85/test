from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.core.collections import collection_from_email
from app.core.dependencies import (
    get_client_repository,
    get_client_service,
    require_permission,
    verify_access_token,
)
from app.core.oauth import AuthenticatedPrincipal
from app.core.rbac import Permission
from app.core.tenant import (
    is_scope_unrestricted,
    principal_email,
    resolve_user_email,
    verify_client_email_scope,
)
from app.db.postgres.client_repository import ClientRepository
from app.schemas.client_resolve import ClientResolveByPhoneResponse
from app.schemas.clients import (
    ClientAdminListResponse,
    ClientAdminProfileResponse,
    ClientApproveRequest,
    ClientDeleteResponse,
    ClientListResponse,
    ClientProfileResponse,
    ClientProfileUpsertRequest,
)
from app.services.client_service import ClientService

router = APIRouter(
    prefix="/v1/clients",
    tags=["clients"],
    dependencies=[Depends(verify_access_token)],
)


@router.get("/me", response_model=ClientProfileResponse)
async def get_my_client_profile(
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    service: Annotated[ClientService, Depends(get_client_service)],
) -> ClientProfileResponse:
    if principal.is_m2m:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client profile is not available for machine clients",
        )

    session_email = request.headers.get("x-relaydesk-user-email")
    resolved_email = resolve_user_email(principal, session_email)

    existing = await service.get_profile_for_principal(
        cognito_sub=principal.subject,
        client_email_id=resolved_email,
    )
    if existing is not None:
        if resolved_email:
            return await service.ensure_on_sign_in(
                client_email_id=resolved_email,
                cognito_sub=principal.subject,
            )
        return existing

    if not resolved_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authenticated user email is required",
        )
    return await service.ensure_on_sign_in(
        client_email_id=resolved_email,
        cognito_sub=principal.subject,
    )


@router.get("", response_model=ClientAdminListResponse)
async def list_clients(
    service: Annotated[ClientService, Depends(get_client_service)],
    _principal: Annotated[object, Depends(require_permission(Permission.ADMIN))] = ...,
) -> ClientAdminListResponse:
    return await service.list_clients_admin()


@router.post(
    "/approve",
    response_model=ClientAdminProfileResponse,
    status_code=status.HTTP_200_OK,
)
async def approve_client(
    body: ClientApproveRequest,
    service: Annotated[ClientService, Depends(get_client_service)],
    _principal: Annotated[object, Depends(require_permission(Permission.ADMIN))] = ...,
) -> ClientAdminProfileResponse:
    normalized_email = body.client_email_id.strip().lower()
    if "@" not in normalized_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid client_email_id",
        )
    try:
        return await service.approve_client(
            client_email_id=normalized_email,
            client_business_phone_number=body.client_business_phone_number,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/account", response_model=ClientDeleteResponse)
async def delete_client(
    client_email_id: Annotated[str, Query(min_length=3, max_length=255)],
    service: Annotated[ClientService, Depends(get_client_service)],
    _principal: Annotated[object, Depends(require_permission(Permission.ADMIN))] = ...,
) -> ClientDeleteResponse:
    normalized = client_email_id.strip().lower()
    if "@" not in normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid client_email_id",
        )
    try:
        return await service.delete_client(normalized)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc
        raise HTTPException(status_code=400, detail=message) from exc


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


@router.get("/resolve-by-phone", response_model=ClientResolveByPhoneResponse)
async def resolve_client_by_phone(
    phone_number: Annotated[str, Query(min_length=5, max_length=32)],
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
) -> ClientResolveByPhoneResponse:
    if not principal.is_m2m:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phone resolution is available to machine clients only",
        )

    client = await repository.get_by_business_phone(phone_number)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No client found for this business phone number",
        )

    return ClientResolveByPhoneResponse(
        client_email_id=client.client_email_id,
        client_name=client.client_name,
        client_business_phone_number=client.client_business_phone_number,
        collection_name=collection_from_email(client.client_email_id),
    )
