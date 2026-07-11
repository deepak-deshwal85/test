from __future__ import annotations

from app.db.postgres.customer_repository import CustomerRepository
from app.domain.customer_models import Customer
from app.schemas.customers import (
    CustomerCreateRequest,
    CustomerResponse,
    CustomerUpdateRequest,
)


class CustomerService:
    def __init__(self, repository: CustomerRepository) -> None:
        self._repository = repository

    @staticmethod
    def _to_response(customer: Customer) -> CustomerResponse:
        return CustomerResponse(
            id=customer.id,
            client_id=customer.client_id,
            client_business_phone_number=customer.client_business_phone_number,
            client_name=customer.client_name,
            client_email_id=customer.client_email_id,
            consumer_phone_number=customer.consumer_phone_number,
            consumer_email_id=customer.consumer_email_id,
            is_approved=customer.is_approved,
            call_schedule=customer.call_schedule,
            status=customer.status,
            created_at=customer.created_at,
            updated_at=customer.updated_at,
        )

    async def create(self, body: CustomerCreateRequest) -> CustomerResponse:
        customer = await self._repository.create(
            client_business_phone_number=body.client_business_phone_number,
            client_name=body.client_name,
            client_email_id=body.client_email_id,
            consumer_phone_number=body.consumer_phone_number,
            consumer_email_id=body.consumer_email_id,
            call_schedule=body.call_schedule,
            status=body.status,
        )
        return self._to_response(customer)

    async def get(
        self, customer_id: int, *, client_email_id: str
    ) -> CustomerResponse | None:
        customer = await self._repository.get(
            customer_id, client_email_id=client_email_id
        )
        return self._to_response(customer) if customer else None

    async def list(
        self,
        *,
        client_email_id: str | None,
        client_business_phone_number: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[CustomerResponse]:
        customers = await self._repository.list(
            client_email_id=client_email_id,
            client_business_phone_number=client_business_phone_number,
            skip=skip,
            limit=limit,
        )
        return [self._to_response(customer) for customer in customers]

    async def update(
        self,
        customer_id: int,
        *,
        client_email_id: str,
        body: CustomerUpdateRequest,
    ) -> CustomerResponse | None:
        customer = await self._repository.update(
            customer_id,
            client_email_id=client_email_id,
            client_business_phone_number=body.client_business_phone_number,
            client_name=body.client_name,
            consumer_email_id=body.consumer_email_id,
            consumer_phone_number=body.consumer_phone_number,
            call_schedule=body.call_schedule,
            status=body.status,
        )
        return self._to_response(customer) if customer else None

    async def delete(self, customer_id: int, *, client_email_id: str) -> bool:
        return await self._repository.delete(
            customer_id, client_email_id=client_email_id
        )

    async def approve(
        self, customer_id: int, *, client_email_id: str
    ) -> CustomerResponse | None:
        customer = await self._repository.approve(
            customer_id, client_email_id=client_email_id
        )
        return self._to_response(customer) if customer else None
