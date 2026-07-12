from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.models import CallJobRow
from app.domain.consumer_models import (
    CallAttemptResult,
    CallJob,
)


class CallJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _parse_results(raw: str | None) -> list[CallAttemptResult] | None:
        if not raw:
            return None
        items = json.loads(raw)
        return [
            CallAttemptResult(
                consumer_id=int(item["consumer_id"]),
                consumer_phone_number=str(item["consumer_phone_number"]),
                success=bool(item["success"]),
                detail=str(item["detail"]),
            )
            for item in items
        ]

    @staticmethod
    def _serialize_results(results: list[CallAttemptResult]) -> str:
        return json.dumps(
            [
                {
                    "consumer_id": result.consumer_id,
                    "consumer_phone_number": result.consumer_phone_number,
                    "success": result.success,
                    "detail": result.detail,
                }
                for result in results
            ]
        )

    def _to_domain(self, row: CallJobRow) -> CallJob:
        return CallJob(
            id=row.id,
            client_id=row.client_id,
            status=row.status,
            total_consumers=row.total_consumers,
            calls_completed=row.calls_completed,
            error_message=row.error_message,
            started_at=row.started_at,
            completed_at=row.completed_at,
            created_at=row.created_at,
            results=self._parse_results(row.results_json),
        )

    async def create(self, *, client_id: int) -> CallJob:
        row = CallJobRow(
            id=uuid4(),
            client_id=client_id,
            status="pending",
        )
        self._session.add(row)
        try:
            await self._session.commit()
        except Exception as exc:
            await self._session.rollback()
            raise
        await self._session.refresh(row)
        return self._to_domain(row)

    async def get(self, job_id: UUID) -> CallJob | None:
        row = await self._session.get(CallJobRow, job_id)
        return self._to_domain(row) if row else None

    async def mark_running(
        self, job_id: UUID, *, total_consumers: int
    ) -> CallJob | None:
        row = await self._session.get(CallJobRow, job_id)
        if row is None:
            return None
        row.status = "running"
        row.total_consumers = total_consumers
        row.started_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_domain(row)

    async def update_progress(
        self,
        job_id: UUID,
        *,
        calls_completed: int,
        results: list[CallAttemptResult] | None = None,
    ) -> None:
        row = await self._session.get(CallJobRow, job_id)
        if row is None:
            return
        row.calls_completed = calls_completed
        if results is not None:
            row.results_json = self._serialize_results(results)
        await self._session.commit()

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        results: list[CallAttemptResult] | None = None,
    ) -> CallJob | None:
        row = await self._session.get(CallJobRow, job_id)
        if row is None:
            return None
        row.status = "completed"
        row.completed_at = datetime.now(UTC)
        if results is not None:
            row.results_json = self._serialize_results(results)
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_domain(row)

    async def mark_failed(
        self,
        job_id: UUID,
        *,
        error_message: str,
        results: list[CallAttemptResult] | None = None,
    ) -> CallJob | None:
        row = await self._session.get(CallJobRow, job_id)
        if row is None:
            return None
        row.status = "failed"
        row.error_message = error_message
        row.completed_at = datetime.now(UTC)
        if results is not None:
            row.results_json = self._serialize_results(results)
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_domain(row)

    async def list_recent(
        self,
        *,
        client_id: int | None = None,
        limit: int = 20,
    ) -> list[CallJob]:
        query = select(CallJobRow).order_by(CallJobRow.created_at.desc()).limit(limit)
        if client_id is not None:
            query = query.where(CallJobRow.client_id == client_id)
        rows = (await self._session.execute(query)).scalars().all()
        return [self._to_domain(row) for row in rows]

    async def has_active_for_client(self, client_id: int) -> bool:
        query = (
            select(CallJobRow.id)
            .where(CallJobRow.client_id == client_id)
            .where(CallJobRow.status.in_(("pending", "running")))
            .limit(1)
        )
        row = (await self._session.execute(query)).scalar_one_or_none()
        return row is not None
