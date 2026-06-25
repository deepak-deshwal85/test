from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.models import CustomerRow
from app.domain.customer_models import Customer, normalize_phone_number


class CustomerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: CustomerRow) -> Customer:
        return Customer(
            id=row.id,
            client_phone_number=row.client_phone_number,
            client_name=row.client_name,
            consumer_phone_number=row.consumer_phone_number,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def create(
        self,
        *,
        client_phone_number: str,
        client_name: str,
        consumer_phone_number: str,
    ) -> Customer:
        row = CustomerRow(
            client_phone_number=normalize_phone_number(client_phone_number),
            client_name=client_name.strip(),
            consumer_phone_number=normalize_phone_number(consumer_phone_number),
        )
        self._session.add(row)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ValueError(
                "Customer already exists for this client and consumer phone number"
            ) from exc
        await self._session.refresh(row)
        return self._to_domain(row)

    async def get(self, customer_id: int) -> Customer | None:
        row = await self._session.get(CustomerRow, customer_id)
        return self._to_domain(row) if row else None

    async def list(
        self,
        *,
        client_phone_number: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Customer]:
        query = select(CustomerRow).order_by(CustomerRow.id)
        if client_phone_number:
            query = query.where(
                CustomerRow.client_phone_number
                == normalize_phone_number(client_phone_number)
            )
        query = query.offset(skip).limit(limit)
        rows = (await self._session.execute(query)).scalars().all()
        return [self._to_domain(row) for row in rows]

    async def list_by_client_phone(self, client_phone_number: str) -> list[Customer]:
        return await self.list(
            client_phone_number=client_phone_number,
            skip=0,
            limit=10_000,
        )

    async def update(
        self,
        customer_id: int,
        *,
        client_phone_number: str | None = None,
        client_name: str | None = None,
        consumer_phone_number: str | None = None,
    ) -> Customer | None:
        row = await self._session.get(CustomerRow, customer_id)
        if row is None:
            return None

        if client_phone_number is not None:
            row.client_phone_number = normalize_phone_number(client_phone_number)
        if client_name is not None:
            row.client_name = client_name.strip()
        if consumer_phone_number is not None:
            row.consumer_phone_number = normalize_phone_number(consumer_phone_number)

        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ValueError(
                "Customer already exists for this client and consumer phone number"
            ) from exc
        await self._session.refresh(row)
        return self._to_domain(row)

    async def delete(self, customer_id: int) -> bool:
        row = await self._session.get(CustomerRow, customer_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True
