from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.db.postgres.call_job_repository import CallJobRepository
from app.db.postgres.customer_repository import CustomerRepository
from app.db.postgres.session import get_session_factory
from app.domain.customer_models import CallAttemptResult
from app.schemas.call_jobs import CallAttemptResponse, CallJobResponse
from app.services.outbound_caller import OutboundCaller, build_outbound_caller

logger = logging.getLogger("relaydesk-api")


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
        results = None
        if job.results:
            results = [
                CallAttemptResponse(
                    customer_id=result.customer_id,
                    consumer_phone_number=result.consumer_phone_number,
                    success=result.success,
                    detail=result.detail,
                )
                for result in job.results
            ]
        return CallJobResponse(
            id=job.id,
            client_business_phone_number=job.client_business_phone_number,
            client_email_id=job.client_email_id,
            status=job.status,
            total_customers=job.total_customers,
            calls_completed=job.calls_completed,
            error_message=job.error_message,
            started_at=job.started_at,
            completed_at=job.completed_at,
            created_at=job.created_at,
            results=results,
        )

    async def create_job(
        self, client_business_phone_number: str, client_email_id: str
    ) -> CallJobResponse:
        async with self._session_factory() as session:
            repository = CallJobRepository(session)
            job = await repository.create(
                client_business_phone_number=client_business_phone_number,
                client_email_id=client_email_id,
            )
            return self._to_response(job)

    async def get_job(
        self, job_id: UUID, *, client_email_id: str | None = None
    ) -> CallJobResponse | None:
        async with self._session_factory() as session:
            repository = CallJobRepository(session)
            job = await repository.get(job_id)
            if (
                job
                and client_email_id
                and job.client_email_id != client_email_id.strip().lower()
            ):
                return None
            return self._to_response(job) if job else None

    async def list_jobs(
        self,
        *,
        client_email_id: str | None = None,
        client_business_phone_number: str | None = None,
        limit: int = 20,
    ) -> list[CallJobResponse]:
        async with self._session_factory() as session:
            repository = CallJobRepository(session)
            jobs = await repository.list_recent(
                client_email_id=client_email_id,
                client_business_phone_number=client_business_phone_number,
                limit=limit,
            )
            return [self._to_response(job) for job in jobs]

    async def run_job(self, job_id: UUID) -> None:
        logger.info("call job started job_id=%s", job_id)
        results: list[CallAttemptResult] = []
        try:
            async with self._session_factory() as session:
                job_repository = CallJobRepository(session)
                customer_repository = CustomerRepository(session)

                job = await job_repository.get(job_id)
                if job is None:
                    logger.error("call job not found job_id=%s", job_id)
                    return

                customers = await customer_repository.list_scheduled_for_campaign(
                    client_business_phone_number=job.client_business_phone_number,
                    client_email_id=job.client_email_id,
                )
                logger.info(
                    "campaign job loaded customers job_id=%s client=%s scheduled=%d",
                    job_id,
                    job.client_business_phone_number,
                    len(customers),
                )
                for customer in customers:
                    logger.info(
                        "customer queued job_id=%s id=%s name=%s consumer=%s",
                        job_id,
                        customer.id,
                        customer.client_name,
                        customer.consumer_phone_number,
                    )

                await job_repository.mark_running(
                    job_id, total_customers=len(customers)
                )

            completed = 0
            for customer in customers:
                result = await self._outbound_caller.place_call(
                    customer=customer,
                    job_id=job_id,
                )
                results.append(result)
                if result.success:
                    completed += 1
                logger.info(
                    "call attempt job_id=%s customer_id=%s consumer=%s success=%s detail=%s",
                    job_id,
                    customer.id,
                    customer.consumer_phone_number,
                    result.success,
                    result.detail,
                )

                async with self._session_factory() as session:
                    job_repository = CallJobRepository(session)
                    await job_repository.update_progress(
                        job_id,
                        calls_completed=completed,
                        results=results,
                    )

            async with self._session_factory() as session:
                job_repository = CallJobRepository(session)
                await job_repository.mark_completed(job_id, results=results)

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
                await job_repository.mark_failed(
                    job_id,
                    error_message=str(exc),
                    results=results or None,
                )


def build_call_job_service(settings: Settings) -> CallJobService:
    return CallJobService(
        settings=settings,
        session_factory=get_session_factory(),
        outbound_caller=build_outbound_caller(settings),
    )
