from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.models import CallSummaryRow, ConsumerRow
from app.domain.call_summary_models import CallSummary


class CallSummaryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(
        row: CallSummaryRow,
        *,
        consumer_phone_number: str | None = None,
        consumer_email_id: str | None = None,
    ) -> CallSummary:
        return CallSummary(
            id=row.id,
            consumer_id=row.consumer_id,
            client_id=row.client_id,
            call_start_time=row.call_start_time,
            call_end_time=row.call_end_time,
            call_summary=row.call_summary,
            job_id=row.job_id,
            created_at=row.created_at,
            consumer_phone_number=consumer_phone_number,
            consumer_email_id=consumer_email_id,
        )

    async def _get_consumer(
        self, consumer_id: int, *, client_id: int | None = None
    ) -> ConsumerRow | None:
        row = await self._session.get(ConsumerRow, consumer_id)
        if row is None:
            return None
        if client_id is not None and row.client_id != client_id:
            return None
        return row

    async def create(
        self,
        *,
        consumer_id: int,
        client_id: int,
        call_start_time: datetime,
        call_end_time: datetime | None,
        call_summary: str,
        job_id: uuid.UUID | None = None,
    ) -> CallSummary:
        consumer = await self._get_consumer(consumer_id, client_id=client_id)
        if consumer is None:
            raise ValueError("Consumer not found for this client")

        row = CallSummaryRow(
            consumer_id=consumer_id,
            client_id=client_id,
            call_start_time=call_start_time,
            call_end_time=call_end_time,
            call_summary=call_summary.strip(),
            job_id=job_id,
        )
        self._session.add(row)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ValueError("Call summary could not be saved") from exc
        await self._session.refresh(row)
        return self._to_domain(
            row,
            consumer_phone_number=consumer.consumer_phone_number,
            consumer_email_id=consumer.consumer_email_id,
        )

    async def get(self, summary_id: int, *, client_id: int) -> CallSummary | None:
        row = await self._session.get(CallSummaryRow, summary_id)
        if row is None or row.client_id != client_id:
            return None
        consumer = await self._session.get(ConsumerRow, row.consumer_id)
        return self._to_domain(
            row,
            consumer_phone_number=consumer.consumer_phone_number if consumer else None,
            consumer_email_id=consumer.consumer_email_id if consumer else None,
        )

    async def list(
        self,
        *,
        client_id: int | None,
        consumer_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[CallSummary]:
        query = (
            select(CallSummaryRow, ConsumerRow)
            .join(ConsumerRow, ConsumerRow.id == CallSummaryRow.consumer_id)
            .order_by(CallSummaryRow.call_start_time.desc())
        )
        if client_id is not None:
            query = query.where(CallSummaryRow.client_id == client_id)
        if consumer_id is not None:
            query = query.where(CallSummaryRow.consumer_id == consumer_id)
        query = query.offset(skip).limit(limit)
        rows = (await self._session.execute(query)).all()
        return [
            self._to_domain(
                summary_row,
                consumer_phone_number=consumer_row.consumer_phone_number,
                consumer_email_id=consumer_row.consumer_email_id,
            )
            for summary_row, consumer_row in rows
        ]

    async def update(
        self,
        summary_id: int,
        *,
        client_id: int,
        call_start_time: datetime | None = None,
        call_end_time: datetime | None = None,
        call_summary: str | None = None,
    ) -> CallSummary | None:
        row = await self._session.get(CallSummaryRow, summary_id)
        if row is None or row.client_id != client_id:
            return None

        if call_start_time is not None:
            row.call_start_time = call_start_time
        if call_end_time is not None:
            row.call_end_time = call_end_time
        if call_summary is not None:
            row.call_summary = call_summary.strip()

        await self._session.commit()
        await self._session.refresh(row)
        consumer = await self._session.get(ConsumerRow, row.consumer_id)
        return self._to_domain(
            row,
            consumer_phone_number=consumer.consumer_phone_number if consumer else None,
            consumer_email_id=consumer.consumer_email_id if consumer else None,
        )

    async def delete(self, summary_id: int, *, client_id: int) -> bool:
        row = await self._session.get(CallSummaryRow, summary_id)
        if row is None or row.client_id != client_id:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True
