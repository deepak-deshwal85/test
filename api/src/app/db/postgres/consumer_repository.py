from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.models import ConsumerRow
from app.domain.consumer_models import Consumer, normalize_email, normalize_phone_number
from app.domain.consumer_status import (
    VALID_CONSUMER_STATUSES,
    consumer_status_after_call,
)

_DUPLICATE_CONSUMER_MESSAGE = (
    "Consumer already exists for this client and consumer phone number"
)


def _raise_from_integrity_error(exc: IntegrityError) -> None:
    message = str(exc.orig or exc).lower()
    if "not-null" in message or "notnull" in message or "null value" in message:
        raise ValueError(
            "Consumer could not be saved because required database fields are missing. "
            "Restart the API to apply schema migrations, then try again."
        ) from exc
    if "unique" in message or "duplicate" in message:
        raise ValueError(_DUPLICATE_CONSUMER_MESSAGE) from exc
    raise ValueError(
        "Consumer could not be saved due to a database constraint."
    ) from exc


class ConsumerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: ConsumerRow) -> Consumer:
        return Consumer(
            id=row.id,
            client_id=row.client_id,
            consumer_phone_number=row.consumer_phone_number,
            consumer_email_id=row.consumer_email_id,
            consumer_name=row.consumer_name,
            consumer_address=row.consumer_address,
            is_approved=row.is_approved,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def _find_by_client_and_phone(
        self,
        *,
        client_id: int,
        consumer_phone_number: str,
        exclude_consumer_id: int | None = None,
    ) -> ConsumerRow | None:
        normalized = normalize_phone_number(consumer_phone_number)
        query = select(ConsumerRow).where(
            ConsumerRow.client_id == client_id,
            ConsumerRow.consumer_phone_number == normalized,
        )
        if exclude_consumer_id is not None:
            query = query.where(ConsumerRow.id != exclude_consumer_id)
        return (await self._session.execute(query)).scalars().first()

    async def create(
        self,
        *,
        client_id: int,
        client_business_phone_number: str,
        consumer_phone_number: str,
        consumer_email_id: str,
        consumer_name: str = "",
        consumer_address: str = "",
        status: str = "READY",
    ) -> Consumer:
        normalized_business = normalize_phone_number(client_business_phone_number)
        normalized_consumer = normalize_phone_number(consumer_phone_number)
        if normalized_consumer == normalized_business:
            raise ValueError(
                "Consumer phone number must be different from the client business phone"
            )

        if await self._find_by_client_and_phone(
            client_id=client_id,
            consumer_phone_number=normalized_consumer,
        ):
            raise ValueError(_DUPLICATE_CONSUMER_MESSAGE)

        row = ConsumerRow(
            client_id=client_id,
            consumer_phone_number=normalized_consumer,
            consumer_email_id=normalize_email(consumer_email_id),
            consumer_name=consumer_name.strip(),
            consumer_address=consumer_address.strip(),
            is_approved=True,
            status=status,
        )
        self._session.add(row)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            _raise_from_integrity_error(exc)
        await self._session.refresh(row)
        return self._to_domain(row)

    async def get(self, consumer_id: int, *, client_id: int) -> Consumer | None:
        row = await self._session.get(ConsumerRow, consumer_id)
        if row is None or row.client_id != client_id:
            return None
        return self._to_domain(row)

    async def get_by_id(self, consumer_id: int) -> Consumer | None:
        row = await self._session.get(ConsumerRow, consumer_id)
        return self._to_domain(row) if row else None

    async def list(
        self,
        *,
        client_id: int | None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Consumer]:
        query = select(ConsumerRow)
        if client_id is not None:
            query = query.where(ConsumerRow.client_id == client_id)
        query = query.order_by(ConsumerRow.id).offset(skip).limit(limit)
        rows = (await self._session.execute(query)).scalars().all()
        return [self._to_domain(row) for row in rows]

    async def list_ready_for_campaign(self, *, client_id: int) -> list[Consumer]:
        """Return consumers with status=READY for this client (campaign trigger condition)."""
        query = (
            select(ConsumerRow)
            .where(ConsumerRow.client_id == client_id)
            .where(ConsumerRow.status == "READY")
            .order_by(ConsumerRow.id)
        )
        rows = (await self._session.execute(query)).scalars().all()
        return [self._to_domain(row) for row in rows]

    async def update(
        self,
        consumer_id: int,
        *,
        client_id: int,
        consumer_email_id: str | None = None,
        consumer_phone_number: str | None = None,
        consumer_name: str | None = None,
        consumer_address: str | None = None,
        status: str | None = None,
    ) -> Consumer | None:
        row = await self._session.get(ConsumerRow, consumer_id)
        if row is None or row.client_id != client_id:
            return None

        if consumer_email_id is not None:
            row.consumer_email_id = normalize_email(consumer_email_id)
        if consumer_name is not None:
            row.consumer_name = consumer_name.strip()
        if consumer_address is not None:
            row.consumer_address = consumer_address.strip()
        if consumer_phone_number is not None:
            normalized_consumer = normalize_phone_number(consumer_phone_number)
            if await self._find_by_client_and_phone(
                client_id=client_id,
                consumer_phone_number=normalized_consumer,
                exclude_consumer_id=consumer_id,
            ):
                raise ValueError(_DUPLICATE_CONSUMER_MESSAGE)
            row.consumer_phone_number = normalized_consumer
        if status is not None:
            if status not in VALID_CONSUMER_STATUSES:
                raise ValueError(
                    "status must be READY, MEETING_SCHEDULED, or MEETING_NOT_SCHEDULED"
                )
            row.status = status

        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            _raise_from_integrity_error(exc)
        await self._session.refresh(row)
        return self._to_domain(row)

    async def update_status_after_call(
        self,
        consumer_id: int,
        *,
        client_id: int,
        meeting_scheduled: bool,
    ) -> Consumer | None:
        return await self.update(
            consumer_id,
            client_id=client_id,
            status=consumer_status_after_call(meeting_scheduled=meeting_scheduled),
        )

    async def delete(self, consumer_id: int, *, client_id: int) -> bool:
        row = await self._session.get(ConsumerRow, consumer_id)
        if row is None or row.client_id != client_id:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    async def approve(self, consumer_id: int, *, client_id: int) -> Consumer | None:
        row = await self._session.get(ConsumerRow, consumer_id)
        if row is None or row.client_id != client_id:
            return None
        row.is_approved = True
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_domain(row)
