from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.db.postgres.call_job_repository import CallJobRepository
from app.db.postgres.customer_repository import CustomerRepository
from app.db.postgres.session import get_session_factory
from app.schemas.call_jobs import CallJobResponse
from app.services.outbound_caller import OutboundCaller

logger = logging.getLogger("telephone-rag-api")


class CallJobService:
    def __init__(
        self,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        outbound_caller: OutboundCaller,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._outbound_caller = outbound_caller

    @staticmethod
    def _to_response(job) -> CallJobResponse:
        return CallJobResponse(
            id=job.id,
            client_phone_number=job.client_phone_number,
            status=job.status,
            total_customers=job.total_customers,
            calls_completed=job.calls_completed,
            error_message=job.error_message,
            started_at=job.started_at,
            completed_at=job.completed_at,
            created_at=job.created_at,
        )

    async def create_job(self, client_phone_number: str) -> CallJobResponse:
        async with self._session_factory() as session:
            repository = CallJobRepository(session)
            job = await repository.create(client_phone_number=client_phone_number)
            return self._to_response(job)

    async def get_job(self, job_id: UUID) -> CallJobResponse | None:
        async with self._session_factory() as session:
            repository = CallJobRepository(session)
            job = await repository.get(job_id)
            return self._to_response(job) if job else None

    async def run_job(self, job_id: UUID) -> None:
        logger.info("call job started job_id=%s", job_id)
        try:
            async with self._session_factory() as session:
                job_repository = CallJobRepository(session)
                customer_repository = CustomerRepository(session)

                job = await job_repository.get(job_id)
                if job is None:
                    logger.error("call job not found job_id=%s", job_id)
                    return

                customers = await customer_repository.list_by_client_phone(
                    job.client_phone_number
                )
                await job_repository.mark_running(
                    job_id, total_customers=len(customers)
                )

            completed = 0
            for customer in customers:
                result = await self._outbound_caller.place_call(customer=customer)
                if result.success:
                    completed += 1

                async with self._session_factory() as session:
                    job_repository = CallJobRepository(session)
                    await job_repository.update_progress(
                        job_id, calls_completed=completed
                    )

            async with self._session_factory() as session:
                job_repository = CallJobRepository(session)
                await job_repository.mark_completed(job_id)

            logger.info(
                "call job completed job_id=%s calls=%d/%d",
                job_id,
                completed,
                len(customers),
            )
        except Exception as exc:
            logger.exception("call job failed job_id=%s", job_id)
            async with self._session_factory() as session:
                job_repository = CallJobRepository(session)
                await job_repository.mark_failed(job_id, error_message=str(exc))


def build_call_job_service(settings: Settings) -> CallJobService:
    return CallJobService(
        settings=settings,
        session_factory=get_session_factory(),
        outbound_caller=OutboundCaller(settings),
    )
