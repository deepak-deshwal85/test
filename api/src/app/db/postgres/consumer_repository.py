from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.models import ClientRow, ConsumerRow
from app.domain.consumer_models import Consumer, normalize_email, normalize_phone_number
from app.domain.consumer_status import (
    VALID_CALL_SCHEDULES,
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
    raise ValueError("Consumer could not be saved due to a database constraint.") from exc


class ConsumerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _find_by_client_and_consumer_phone(
        self,
        *,
        client_email_id: str,
        client_business_phone_number: str,
        consumer_phone_number: str,
        exclude_consumer_id: int | None = None,
    ) -> ConsumerRow | None:
        normalized_email = normalize_email(client_email_id)
        normalized_consumer = normalize_phone_number(consumer_phone_number)

        query = select(ConsumerRow).where(
            ConsumerRow.client_email_id == normalized_email,
            ConsumerRow.consumer_phone_number == normalized_consumer,
        )
        if exclude_consumer_id is not None:
            query = query.where(ConsumerRow.id != exclude_consumer_id)

        return (await self._session.execute(query)).scalars().first()

    @staticmethod
    def _duplicate_consumer_error() -> ValueError:
        return ValueError(_DUPLICATE_CONSUMER_MESSAGE)

    @staticmethod
    def _to_domain(row: ConsumerRow) -> Consumer:
        return Consumer(
            id=row.id,
            client_id=row.client_id,
            client_business_phone_number=row.client_business_phone_number,
            client_name=row.client_name,
            client_email_id=row.client_email_id,
            consumer_phone_number=row.consumer_phone_number,
            consumer_email_id=row.consumer_email_id,
            is_approved=row.is_approved,
            call_schedule=row.call_schedule,
            status=row.status,
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
        call_schedule: str = "no",
        status: str = "READY",
    ) -> Consumer:
        normalized_business = normalize_phone_number(client_business_phone_number)
        normalized_consumer = normalize_phone_number(consumer_phone_number)
        if normalized_consumer == normalized_business:
            raise ValueError(
                "Consumer phone number must be different from the client business phone"
            )

        if await self._find_by_client_and_consumer_phone(
            client_email_id=client_email_id,
            client_business_phone_number=client_business_phone_number,
            consumer_phone_number=consumer_phone_number,
        ):
            raise self._duplicate_consumer_error()

        row = ConsumerRow(
            client_business_phone_number=normalized_business,
            client_name=client_name.strip(),
            client_email_id=normalize_email(client_email_id),
            consumer_phone_number=normalized_consumer,
            consumer_email_id=normalize_email(consumer_email_id),
            is_approved=True,
            call_schedule=call_schedule,
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

    async def get(self, consumer_id: int, *, client_email_id: str) -> Consumer | None:
        row = await self._session.get(ConsumerRow, consumer_id)
        if row is None:
            return None
        if row.client_email_id != normalize_email(client_email_id):
            return None
        return self._to_domain(row) if row else None

    async def get_by_id(self, consumer_id: int) -> Consumer | None:
        row = await self._session.get(ConsumerRow, consumer_id)
        return self._to_domain(row) if row else None

    async def list(
        self,
        *,
        client_email_id: str | None,
        client_business_phone_number: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Consumer]:
        query = select(ConsumerRow)
        if client_email_id:
            query = query.where(
                ConsumerRow.client_email_id == normalize_email(client_email_id)
            )
        query = query.order_by(ConsumerRow.id)
        if client_business_phone_number:
            query = query.where(
                ConsumerRow.client_business_phone_number
                == normalize_phone_number(client_business_phone_number)
            )
        query = query.offset(skip).limit(limit)
        rows = (await self._session.execute(query)).scalars().all()
        return [self._to_domain(row) for row in rows]

    async def list_scheduled_for_campaign(
        self, *, client_business_phone_number: str, client_email_id: str
    ) -> list[Consumer]:
        query = (
            select(ConsumerRow)
            .where(ConsumerRow.client_email_id == normalize_email(client_email_id))
            .where(
                ConsumerRow.client_business_phone_number
                == normalize_phone_number(client_business_phone_number)
            )
            .where(ConsumerRow.call_schedule == "yes")
            .where(ConsumerRow.status == "READY")
            .order_by(ConsumerRow.id)
        )
        rows = (await self._session.execute(query)).scalars().all()
        return [self._to_domain(row) for row in rows]

    async def list_approved_by_client(
        self, *, client_business_phone_number: str, client_email_id: str
    ) -> list[Consumer]:
        """Deprecated: use list_scheduled_for_campaign."""
        return await self.list_scheduled_for_campaign(
            client_business_phone_number=client_business_phone_number,
            client_email_id=client_email_id,
        )

    async def update(
        self,
        consumer_id: int,
        *,
        client_email_id: str,
        client_business_phone_number: str | None = None,
        client_name: str | None = None,
        consumer_email_id: str | None = None,
        consumer_phone_number: str | None = None,
        call_schedule: str | None = None,
        status: str | None = None,
    ) -> Consumer | None:
        row = await self._session.get(ConsumerRow, consumer_id)
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
            normalized_consumer = normalize_phone_number(consumer_phone_number)
            normalized_business = row.client_business_phone_number
            if normalized_consumer == normalized_business:
                raise ValueError(
                    "Consumer phone number must be different from the client business phone"
                )
            if await self._find_by_client_and_consumer_phone(
                client_email_id=row.client_email_id,
                client_business_phone_number=normalized_business,
                consumer_phone_number=normalized_consumer,
                exclude_consumer_id=consumer_id,
            ):
                raise self._duplicate_consumer_error()
            row.consumer_phone_number = normalized_consumer
        if call_schedule is not None:
            if call_schedule not in VALID_CALL_SCHEDULES:
                raise ValueError("call_schedule must be 'yes' or 'no'")
            row.call_schedule = call_schedule
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
        client_email_id: str,
        meeting_scheduled: bool,
    ) -> Consumer | None:
        return await self.update(
            consumer_id,
            client_email_id=client_email_id,
            status=consumer_status_after_call(meeting_scheduled=meeting_scheduled),
        )

    async def delete(self, consumer_id: int, *, client_email_id: str) -> bool:
        row = await self._session.get(ConsumerRow, consumer_id)
        if row is None:
            return False
        if row.client_email_id != normalize_email(client_email_id):
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    async def approve(
        self, consumer_id: int, *, client_email_id: str
    ) -> Consumer | None:
        row = await self._session.get(ConsumerRow, consumer_id)
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
