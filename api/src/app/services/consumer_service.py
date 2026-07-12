from __future__ import annotations

from app.db.postgres.consumer_repository import ConsumerRepository
from app.domain.consumer_models import Consumer
from app.schemas.consumers import (
    ConsumerCreateRequest,
    ConsumerResponse,
    ConsumerUpdateRequest,
)


class ConsumerService:
    def __init__(self, repository: ConsumerRepository) -> None:
        self._repository = repository

    @staticmethod
    def _to_response(consumer: Consumer) -> ConsumerResponse:
        return ConsumerResponse(
            id=consumer.id,
            client_id=consumer.client_id,
            client_business_phone_number=consumer.client_business_phone_number,
            client_name=consumer.client_name,
            client_email_id=consumer.client_email_id,
            consumer_phone_number=consumer.consumer_phone_number,
            consumer_email_id=consumer.consumer_email_id,
            is_approved=consumer.is_approved,
            call_schedule=consumer.call_schedule,
            status=consumer.status,
            created_at=consumer.created_at,
            updated_at=consumer.updated_at,
        )

    async def create(self, body: ConsumerCreateRequest) -> ConsumerResponse:
        consumer = await self._repository.create(
            client_business_phone_number=body.client_business_phone_number,
            client_name=body.client_name,
            client_email_id=body.client_email_id,
            consumer_phone_number=body.consumer_phone_number,
            consumer_email_id=body.consumer_email_id,
            call_schedule=body.call_schedule,
            status=body.status,
        )
        return self._to_response(consumer)

    async def get(
        self, consumer_id: int, *, client_email_id: str
    ) -> ConsumerResponse | None:
        consumer = await self._repository.get(
            consumer_id, client_email_id=client_email_id
        )
        return self._to_response(consumer) if consumer else None

    async def get_by_id(self, consumer_id: int) -> ConsumerResponse | None:
        consumer = await self._repository.get_by_id(consumer_id)
        return self._to_response(consumer) if consumer else None

    async def list(
        self,
        *,
        client_email_id: str | None,
        client_business_phone_number: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ConsumerResponse]:
        consumers = await self._repository.list(
            client_email_id=client_email_id,
            client_business_phone_number=client_business_phone_number,
            skip=skip,
            limit=limit,
        )
        return [self._to_response(consumer) for consumer in consumers]

    async def update(
        self,
        consumer_id: int,
        *,
        client_email_id: str,
        body: ConsumerUpdateRequest,
    ) -> ConsumerResponse | None:
        consumer = await self._repository.update(
            consumer_id,
            client_email_id=client_email_id,
            client_business_phone_number=body.client_business_phone_number,
            client_name=body.client_name,
            consumer_email_id=body.consumer_email_id,
            consumer_phone_number=body.consumer_phone_number,
            call_schedule=body.call_schedule,
            status=body.status,
        )
        return self._to_response(consumer) if consumer else None

    async def delete(self, consumer_id: int, *, client_email_id: str) -> bool:
        return await self._repository.delete(
            consumer_id, client_email_id=client_email_id
        )

    async def approve(
        self, consumer_id: int, *, client_email_id: str
    ) -> ConsumerResponse | None:
        consumer = await self._repository.approve(
            consumer_id, client_email_id=client_email_id
        )
        return self._to_response(consumer) if consumer else None
