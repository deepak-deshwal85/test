from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.models import CallSummaryRow, CustomerRow
from app.domain.call_summary_models import CallSummary
from app.domain.customer_models import normalize_email


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
            customer_id=row.customer_id,
            client_email_id=row.client_email_id,
            call_start_time=row.call_start_time,
            call_end_time=row.call_end_time,
            call_summary=row.call_summary,
            job_id=row.job_id,
            created_at=row.created_at,
            consumer_phone_number=consumer_phone_number,
            consumer_email_id=consumer_email_id,
        )

    async def _get_customer(
        self, customer_id: int, *, client_email_id: str | None = None
    ) -> CustomerRow | None:
        row = await self._session.get(CustomerRow, customer_id)
        if row is None:
            return None
        if client_email_id is not None and row.client_email_id != normalize_email(
            client_email_id
        ):
            return None
        return row

    async def create(
        self,
        *,
        customer_id: int,
        client_email_id: str,
        call_start_time: datetime,
        call_end_time: datetime | None,
        call_summary: str,
        job_id: uuid.UUID | None = None,
    ) -> CallSummary:
        customer = await self._get_customer(
            customer_id, client_email_id=client_email_id
        )
        if customer is None:
            raise ValueError("Customer not found for this client")

        row = CallSummaryRow(
            customer_id=customer_id,
            client_email_id=normalize_email(client_email_id),
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
            consumer_phone_number=customer.consumer_phone_number,
            consumer_email_id=customer.consumer_email_id,
        )

    async def get(self, summary_id: int, *, client_email_id: str) -> CallSummary | None:
        row = await self._session.get(CallSummaryRow, summary_id)
        if row is None:
            return None
        if row.client_email_id != normalize_email(client_email_id):
            return None
        customer = await self._session.get(CustomerRow, row.customer_id)
        return self._to_domain(
            row,
            consumer_phone_number=customer.consumer_phone_number if customer else None,
            consumer_email_id=customer.consumer_email_id if customer else None,
        )

    async def list(
        self,
        *,
        client_email_id: str | None,
        customer_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[CallSummary]:
        query = (
            select(CallSummaryRow, CustomerRow)
            .join(CustomerRow, CustomerRow.id == CallSummaryRow.customer_id)
            .order_by(CallSummaryRow.call_start_time.desc())
        )
        if client_email_id:
            query = query.where(
                CallSummaryRow.client_email_id == normalize_email(client_email_id)
            )
        if customer_id is not None:
            query = query.where(CallSummaryRow.customer_id == customer_id)
        query = query.offset(skip).limit(limit)
        rows = (await self._session.execute(query)).all()
        return [
            self._to_domain(
                summary_row,
                consumer_phone_number=customer_row.consumer_phone_number,
                consumer_email_id=customer_row.consumer_email_id,
            )
            for summary_row, customer_row in rows
        ]

    async def update(
        self,
        summary_id: int,
        *,
        client_email_id: str,
        call_start_time: datetime | None = None,
        call_end_time: datetime | None = None,
        call_summary: str | None = None,
    ) -> CallSummary | None:
        row = await self._session.get(CallSummaryRow, summary_id)
        if row is None:
            return None
        if row.client_email_id != normalize_email(client_email_id):
            return None

        if call_start_time is not None:
            row.call_start_time = call_start_time
        if call_end_time is not None:
            row.call_end_time = call_end_time
        if call_summary is not None:
            row.call_summary = call_summary.strip()

        await self._session.commit()
        await self._session.refresh(row)
        customer = await self._session.get(CustomerRow, row.customer_id)
        return self._to_domain(
            row,
            consumer_phone_number=customer.consumer_phone_number if customer else None,
            consumer_email_id=customer.consumer_email_id if customer else None,
        )

    async def delete(self, summary_id: int, *, client_email_id: str) -> bool:
        row = await self._session.get(CallSummaryRow, summary_id)
        if row is None:
            return False
        if row.client_email_id != normalize_email(client_email_id):
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True
