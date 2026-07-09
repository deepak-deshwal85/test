from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.models import ClientRow, CustomerRow
from app.domain.customer_models import Customer, normalize_email, normalize_phone_number


class CustomerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: CustomerRow) -> Customer:
        return Customer(
            id=row.id,
            client_id=row.client_id,
            client_business_phone_number=row.client_business_phone_number,
            client_name=row.client_name,
            client_email_id=row.client_email_id,
            consumer_phone_number=row.consumer_phone_number,
            consumer_email_id=row.consumer_email_id,
            is_approved=row.is_approved,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def create(
        self,
        *,
        client_business_phone_number: str,
        client_name: str,
        client_email_id: str,
        consumer_phone_number: str,
        consumer_email_id: str,
    ) -> Customer:
        row = CustomerRow(
            client_business_phone_number=normalize_phone_number(
                client_business_phone_number
            ),
            client_name=client_name.strip(),
            client_email_id=normalize_email(client_email_id),
            consumer_phone_number=normalize_phone_number(consumer_phone_number),
            consumer_email_id=normalize_email(consumer_email_id),
            is_approved=False,
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

    async def get(self, customer_id: int, *, client_email_id: str) -> Customer | None:
        row = await self._session.get(CustomerRow, customer_id)
        if row is None:
            return None
        if row.client_email_id != normalize_email(client_email_id):
            return None
        return self._to_domain(row) if row else None

    async def list(
        self,
        *,
        client_email_id: str | None,
        client_business_phone_number: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Customer]:
        query = select(CustomerRow)
        if client_email_id:
            query = query.where(
                CustomerRow.client_email_id == normalize_email(client_email_id)
            )
        query = query.order_by(CustomerRow.id)
        if client_business_phone_number:
            query = query.where(
                CustomerRow.client_business_phone_number
                == normalize_phone_number(client_business_phone_number)
            )
        query = query.offset(skip).limit(limit)
        rows = (await self._session.execute(query)).scalars().all()
        return [self._to_domain(row) for row in rows]

    async def list_approved_by_client(
        self, *, client_business_phone_number: str, client_email_id: str
    ) -> list[Customer]:
        query = (
            select(CustomerRow)
            .where(CustomerRow.client_email_id == normalize_email(client_email_id))
            .where(
                CustomerRow.client_business_phone_number
                == normalize_phone_number(client_business_phone_number)
            )
            .where(CustomerRow.is_approved.is_(True))
            .order_by(CustomerRow.id)
        )
        rows = (await self._session.execute(query)).scalars().all()
        return [self._to_domain(row) for row in rows]

    async def update(
        self,
        customer_id: int,
        *,
        client_email_id: str,
        client_business_phone_number: str | None = None,
        client_name: str | None = None,
        consumer_email_id: str | None = None,
        consumer_phone_number: str | None = None,
    ) -> Customer | None:
        row = await self._session.get(CustomerRow, customer_id)
        if row is None:
            return None
        if row.client_email_id != normalize_email(client_email_id):
            return None

        if client_business_phone_number is not None:
            row.client_business_phone_number = normalize_phone_number(
                client_business_phone_number
            )
        if client_name is not None:
            row.client_name = client_name.strip()
        if consumer_email_id is not None:
            row.consumer_email_id = normalize_email(consumer_email_id)
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

    async def delete(self, customer_id: int, *, client_email_id: str) -> bool:
        row = await self._session.get(CustomerRow, customer_id)
        if row is None:
            return False
        if row.client_email_id != normalize_email(client_email_id):
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    async def approve(
        self, customer_id: int, *, client_email_id: str
    ) -> Customer | None:
        row = await self._session.get(CustomerRow, customer_id)
        if row is None:
            return None
        normalized_email = normalize_email(client_email_id)
        if row.client_email_id != normalized_email:
            return None

        client = (
            await self._session.execute(
                select(ClientRow).where(ClientRow.client_email_id == normalized_email)
            )
        ).scalar_one_or_none()
        if client is None:
            client = ClientRow(
                client_phone_number=None,
                client_business_phone_number=row.client_business_phone_number,
                client_name=row.client_name,
                client_email_id=normalized_email,
            )
            self._session.add(client)
            await self._session.flush()

        row.client_id = client.id
        row.is_approved = True
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_domain(row)
