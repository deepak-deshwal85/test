from __future__ import annotations

from app.db.postgres.call_summary_repository import CallSummaryRepository
from app.db.postgres.consumer_repository import ConsumerRepository
from app.domain.call_summary_models import CallSummary
from app.domain.consumer_models import normalize_email
from app.schemas.call_summaries import (
    CallSummaryCreateRequest,
    CallSummaryResponse,
    CallSummaryUpdateRequest,
)


class CallSummaryService:
    def __init__(
        self,
        repository: CallSummaryRepository,
        consumer_repository: ConsumerRepository,
    ) -> None:
        self._repository = repository
        self._consumer_repository = consumer_repository

    @staticmethod
    def _to_response(summary: CallSummary) -> CallSummaryResponse:
        return CallSummaryResponse(
            id=summary.id,
            consumer_id=summary.consumer_id,
            client_id=summary.client_id,
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
        client_id: int,
        body: CallSummaryCreateRequest,
    ) -> CallSummaryResponse:
        summary = await self._repository.create(
            consumer_id=body.consumer_id,
            client_id=client_id,
            call_start_time=body.call_start_time,
            call_end_time=body.call_end_time,
            call_summary=body.call_summary,
            job_id=body.job_id,
        )
        await self._consumer_repository.update_status_after_call(
            body.consumer_id,
            client_id=client_id,
            meeting_scheduled=body.meeting_scheduled,
        )
        return self._to_response(summary)

    async def get(
        self, summary_id: int, *, client_id: int
    ) -> CallSummaryResponse | None:
        summary = await self._repository.get(summary_id, client_id=client_id)
        return self._to_response(summary) if summary else None

    async def list(
        self,
        *,
        client_id: int | None,
        consumer_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[CallSummaryResponse]:
        summaries = await self._repository.list(
            client_id=client_id,
            consumer_id=consumer_id,
            skip=skip,
            limit=limit,
        )
        return [self._to_response(summary) for summary in summaries]

    async def update(
        self,
        summary_id: int,
        *,
        client_id: int,
        body: CallSummaryUpdateRequest,
    ) -> CallSummaryResponse | None:
        summary = await self._repository.update(
            summary_id,
            client_id=client_id,
            call_start_time=body.call_start_time,
            call_end_time=body.call_end_time,
            call_summary=body.call_summary,
        )
        return self._to_response(summary) if summary else None

    async def delete(self, summary_id: int, *, client_id: int) -> bool:
        return await self._repository.delete(summary_id, client_id=client_id)
