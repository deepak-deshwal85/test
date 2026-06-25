from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_customer_service, verify_api_key
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
    dependencies=[Depends(verify_api_key)],
)


@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    body: CustomerCreateRequest,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> CustomerResponse:
    try:
        return await service.create(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=CustomerListResponse)
async def list_customers(
    service: Annotated[CustomerService, Depends(get_customer_service)],
    client_phone_number: Annotated[str | None, Query()] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> CustomerListResponse:
    customers = await service.list(
        client_phone_number=client_phone_number,
        skip=skip,
        limit=limit,
    )
    return CustomerListResponse(customers=customers, count=len(customers))


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: int,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> CustomerResponse:
    customer = await service.get(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: int,
    body: CustomerUpdateRequest,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> CustomerResponse:
    try:
        customer = await service.update(customer_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: int,
    service: Annotated[CustomerService, Depends(get_customer_service)],
) -> None:
    deleted = await service.delete(customer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Customer not found")
