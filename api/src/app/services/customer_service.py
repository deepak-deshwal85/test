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
            client_phone_number=customer.client_phone_number,
            client_name=customer.client_name,
            consumer_phone_number=customer.consumer_phone_number,
            created_at=customer.created_at,
            updated_at=customer.updated_at,
        )

    async def create(self, body: CustomerCreateRequest) -> CustomerResponse:
        customer = await self._repository.create(
            client_phone_number=body.client_phone_number,
            client_name=body.client_name,
            consumer_phone_number=body.consumer_phone_number,
        )
        return self._to_response(customer)

    async def get(self, customer_id: int) -> CustomerResponse | None:
        customer = await self._repository.get(customer_id)
        return self._to_response(customer) if customer else None

    async def list(
        self,
        *,
        client_phone_number: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[CustomerResponse]:
        customers = await self._repository.list(
            client_phone_number=client_phone_number,
            skip=skip,
            limit=limit,
        )
        return [self._to_response(customer) for customer in customers]

    async def update(
        self,
        customer_id: int,
        body: CustomerUpdateRequest,
    ) -> CustomerResponse | None:
        customer = await self._repository.update(
            customer_id,
            client_phone_number=body.client_phone_number,
            client_name=body.client_name,
            consumer_phone_number=body.consumer_phone_number,
        )
        return self._to_response(customer) if customer else None

    async def delete(self, customer_id: int) -> bool:
        return await self._repository.delete(customer_id)
