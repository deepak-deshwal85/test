from __future__ import annotations

from app.db.postgres.call_summary_repository import CallSummaryRepository
from app.db.postgres.customer_repository import CustomerRepository
from app.domain.call_summary_models import CallSummary
from app.schemas.call_summaries import (
    CallSummaryCreateRequest,
    CallSummaryResponse,
    CallSummaryUpdateRequest,
)


class CallSummaryService:
    def __init__(
        self,
        repository: CallSummaryRepository,
        customer_repository: CustomerRepository,
    ) -> None:
        self._repository = repository
        self._customer_repository = customer_repository

    @staticmethod
    def _to_response(summary: CallSummary) -> CallSummaryResponse:
        return CallSummaryResponse(
            id=summary.id,
            customer_id=summary.customer_id,
            client_email_id=summary.client_email_id,
            call_start_time=summary.call_start_time,
            call_end_time=summary.call_end_time,
            call_summary=summary.call_summary,
            job_id=summary.job_id,
            created_at=summary.created_at,
            consumer_phone_number=summary.consumer_phone_number,
            consumer_email_id=summary.consumer_email_id,
        )

    async def create(
        self,
        *,
        client_email_id: str,
        body: CallSummaryCreateRequest,
    ) -> CallSummaryResponse:
        summary = await self._repository.create(
            customer_id=body.customer_id,
            client_email_id=client_email_id,
            call_start_time=body.call_start_time,
            call_end_time=body.call_end_time,
            call_summary=body.call_summary,
            job_id=body.job_id,
        )
        await self._customer_repository.update_status_after_call(
            body.customer_id,
            client_email_id=client_email_id,
            meeting_scheduled=body.meeting_scheduled,
        )
        return self._to_response(summary)

    async def get(
        self, summary_id: int, *, client_email_id: str
    ) -> CallSummaryResponse | None:
        summary = await self._repository.get(summary_id, client_email_id=client_email_id)
        return self._to_response(summary) if summary else None

    async def list(
        self,
        *,
        client_email_id: str | None,
        customer_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[CallSummaryResponse]:
        summaries = await self._repository.list(
            client_email_id=client_email_id,
            customer_id=customer_id,
            skip=skip,
            limit=limit,
        )
        return [self._to_response(summary) for summary in summaries]

    async def update(
        self,
        summary_id: int,
        *,
        client_email_id: str,
        body: CallSummaryUpdateRequest,
    ) -> CallSummaryResponse | None:
        summary = await self._repository.update(
            summary_id,
            client_email_id=client_email_id,
            call_start_time=body.call_start_time,
            call_end_time=body.call_end_time,
            call_summary=body.call_summary,
        )
        return self._to_response(summary) if summary else None

    async def delete(self, summary_id: int, *, client_email_id: str) -> bool:
        return await self._repository.delete(summary_id, client_email_id=client_email_id)
