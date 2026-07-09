from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import (
    get_client_repository,
    get_customer_service,
    require_permission,
    verify_access_token,
)
from app.core.oauth import AuthenticatedPrincipal
from app.core.rbac import Permission
from app.core.tenant import is_scope_unrestricted, principal_email, verify_client_email_scope
from app.db.postgres.client_repository import ClientRepository
from app.schemas.customers import (
    CustomerCreateRequest,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdateRequest,
)
from app.services.customer_service import CustomerService

router = APIRouter(
    prefix="/v1/customers",
    tags=["customers"],
    dependencies=[Depends(verify_access_token)],
)


async def _validate_customer_write_scope(
    principal: AuthenticatedPrincipal,
    body_email: str,
    body_business_phone: str | None,
    repository: ClientRepository,
) -> str:
    scoped_email = await verify_client_email_scope(principal, body_email, repository)
    if is_scope_unrestricted(principal):
        return scoped_email

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
    if (
        body_business_phone
        and body_business_phone != client.client_business_phone_number
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client business phone number cannot be changed",
        )
    return scoped_email


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    body: CustomerCreateRequest,
    service: Annotated[CustomerService, Depends(get_customer_service)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(require_permission(Permission.DOCUMENT_WRITE)),
    ],
) -> CustomerResponse:
    scoped_email = await _validate_customer_write_scope(
        principal,
        body.client_email_id,
        body.client_business_phone_number,
        repository,
    )
    if not is_scope_unrestricted(principal):
        client = await repository.get_by_email(scoped_email)
        if client is None:
            raise HTTPException(status_code=404, detail="Client profile not found")
        body = body.model_copy(
            update={
                "client_email_id": client.client_email_id,
                "client_business_phone_number": client.client_business_phone_number,
                "client_name": client.client_name or body.client_name,
            }
        )
    try:
        return await service.create(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    service: Annotated[CustomerService, Depends(get_customer_service)],
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    client_email_id: Annotated[str | None, Query(min_length=3)] = None,
    client_business_phone_number: Annotated[str | None, Query()] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> CustomerListResponse:
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
    customers = await service.list(
        client_email_id=scoped_email,
        client_business_phone_number=client_business_phone_number,
        skip=skip,
        limit=limit,
    )
    return CustomerListResponse(customers=customers, count=len(customers))


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: int,
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    client_email_id: Annotated[str, Query(min_length=3)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> CustomerResponse:
    scoped_email = await verify_client_email_scope(
        principal, client_email_id, repository
    )
    customer = await service.get(customer_id, client_email_id=scoped_email)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    client_email_id: Annotated[str, Query(min_length=3)],
    body: CustomerUpdateRequest,
    service: Annotated[CustomerService, Depends(get_customer_service)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(require_permission(Permission.DOCUMENT_WRITE)),
    ],
) -> CustomerResponse:
    scoped_email = await _validate_customer_write_scope(
        principal,
        client_email_id,
        body.client_business_phone_number,
        repository,
    )
    if not is_scope_unrestricted(principal):
        body = body.model_copy(
            update={
                "client_business_phone_number": None,
                "client_email_id": None,
            }
        )
    try:
        customer = await service.update(
            customer_id,
            client_email_id=scoped_email,
            body=body,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: int,
    client_email_id: Annotated[str, Query(min_length=3)],
    service: Annotated[CustomerService, Depends(get_customer_service)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(require_permission(Permission.DOCUMENT_WRITE)),
    ],
) -> None:
    scoped_email = await verify_client_email_scope(
        principal, client_email_id, repository
    )
    deleted = await service.delete(customer_id, client_email_id=scoped_email)
    if not deleted:
        raise HTTPException(status_code=404, detail="Customer not found")


@router.post(
    "/{customer_id}/approve",
    response_model=CustomerResponse,
    status_code=status.HTTP_200_OK,
)
async def approve_customer(
    customer_id: int,
    client_email_id: Annotated[str, Query(min_length=3)],
    service: Annotated[CustomerService, Depends(get_customer_service)],
    _principal: Annotated[object, Depends(require_permission(Permission.ADMIN))] = ...,
) -> CustomerResponse:
    customer = await service.approve(customer_id, client_email_id=client_email_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer
