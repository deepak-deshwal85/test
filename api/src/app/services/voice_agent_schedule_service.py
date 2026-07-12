from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.postgres.call_job_repository import CallJobRepository
from app.db.postgres.client_repository import ClientRepository
from app.db.postgres.consumer_repository import ConsumerRepository
from app.db.postgres.voice_agent_schedule_repository import VoiceAgentScheduleRepository
from app.domain.voice_agent_schedule_models import VoiceAgentSchedule
from app.schemas.voice_agent_schedules import (
    VoiceAgentScheduleOverviewResponse,
    VoiceAgentScheduleResponse,
    VoiceAgentScheduleTriggerResponse,
    VoiceAgentScheduleUpdateRequest,
)
from app.services.call_job_service import CallJobService
from app.services.client_voice_agent_config_service import ClientVoiceAgentConfigService

logger = logging.getLogger("relaydesk-api")


class VoiceAgentScheduleService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        call_job_service: CallJobService,
        config_service: ClientVoiceAgentConfigService | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._config_service = config_service
        self._call_job_service = call_job_service

    def _require_config_service(self) -> ClientVoiceAgentConfigService:
        if self._config_service is None:
            raise RuntimeError("Voice agent config service is not configured")
        return self._config_service

    @staticmethod
    def _to_response(schedule: VoiceAgentSchedule) -> VoiceAgentScheduleResponse:
        return VoiceAgentScheduleResponse(
            id=schedule.id,
            client_id=schedule.client_id,
            enabled=schedule.enabled,
            run_time=schedule.run_time,
            days_of_week=list(schedule.days_of_week),
            timezone=schedule.timezone,
            next_run_at=schedule.next_run_at,
            last_run_at=schedule.last_run_at,
            last_job_id=schedule.last_job_id,
            created_at=schedule.created_at,
            updated_at=schedule.updated_at,
        )

    async def get_overview(self, *, client_email_id: str) -> VoiceAgentScheduleOverviewResponse:
        voice_config = await self._require_config_service().get(
            client_email_id=client_email_id
        )

        async with self._session_factory() as session:
            schedule_repository = VoiceAgentScheduleRepository(session)
            consumer_repository = ConsumerRepository(session)
            call_job_repository = CallJobRepository(session)

            schedule = await schedule_repository.get_or_create_default(
                voice_config.client_id
            )
            ready_consumers = await consumer_repository.list_ready_for_campaign(
                client_id=voice_config.client_id
            )
            has_active_job = await call_job_repository.has_active_for_client(
                voice_config.client_id
            )

        return VoiceAgentScheduleOverviewResponse(
            client_email_id=voice_config.client_email_id,
            client_name=voice_config.client_name,
            client_business_phone_number=voice_config.client_business_phone_number,
            ready_consumer_count=len(ready_consumers),
            has_active_job=has_active_job,
            voice_agent_config=voice_config,
            schedule=self._to_response(schedule),
        )

    async def update(
        self,
        *,
        client_email_id: str,
        body: VoiceAgentScheduleUpdateRequest,
    ) -> VoiceAgentScheduleOverviewResponse:
        voice_config = await self._require_config_service().get(
            client_email_id=client_email_id
        )

        async with self._session_factory() as session:
            schedule_repository = VoiceAgentScheduleRepository(session)
            schedule = await schedule_repository.upsert(
                client_id=voice_config.client_id,
                enabled=body.enabled,
                run_time=body.run_time,
                days_of_week=body.days_of_week,
                timezone=body.timezone,
            )

        logger.info(
            "voice agent schedule updated client_id=%s enabled=%s run_time=%s",
            voice_config.client_id,
            schedule.enabled,
            schedule.run_time,
        )
        return await self.get_overview(client_email_id=client_email_id)

    async def trigger_now(
        self,
        *,
        client_email_id: str,
        run_job: bool = True,
    ) -> VoiceAgentScheduleTriggerResponse:
        overview = await self.get_overview(client_email_id=client_email_id)
        client = overview.voice_agent_config

        if not client.client_business_phone_number:
            raise ValueError("Client business phone number is not configured")
        if overview.has_active_job:
            raise ValueError("A campaign is already running for this client")
        if overview.ready_consumer_count == 0:
            raise ValueError(
                "No consumers with status Ready — set at least one consumer to Ready"
            )

        job = await self._call_job_service.create_job(client.client_id)

        async with self._session_factory() as session:
            schedule_repository = VoiceAgentScheduleRepository(session)
            schedule = await schedule_repository.get_or_create_default(client.client_id)
            await schedule_repository.mark_triggered(
                schedule.id,
                job_id=job.id,
                triggered_at=datetime.now(UTC),
            )

        if run_job:
            await self._call_job_service.run_job(job.id)

        return VoiceAgentScheduleTriggerResponse(
            job_id=job.id,
            status=job.status,
            message=(
                f"Campaign queued for client {client.client_business_phone_number}. "
                f"{overview.ready_consumer_count} ready consumer(s)."
            ),
        )

    async def execute_due(self, *, run_jobs: bool = True) -> list[UUID]:
        now = datetime.now(UTC)
        triggered_job_ids: list[UUID] = []

        async with self._session_factory() as session:
            schedule_repository = VoiceAgentScheduleRepository(session)
            client_repository = ClientRepository(session)
            consumer_repository = ConsumerRepository(session)
            call_job_repository = CallJobRepository(session)

            due_schedules = await schedule_repository.list_due(before=now)
            for schedule in due_schedules:
                client = await client_repository.get_by_id(schedule.client_id)
                if client is None:
                    continue
                if not client.client_business_phone_number:
                    logger.warning(
                        "skipping scheduled job — no business phone client_id=%s",
                        schedule.client_id,
                    )
                    continue
                if await call_job_repository.has_active_for_client(schedule.client_id):
                    logger.info(
                        "skipping scheduled job — active job exists client_id=%s",
                        schedule.client_id,
                    )
                    continue
                ready = await consumer_repository.list_ready_for_campaign(
                    client_id=schedule.client_id
                )
                if not ready:
                    logger.info(
                        "skipping scheduled job — no ready consumers client_id=%s",
                        schedule.client_id,
                    )
                    await schedule_repository.reschedule_next_run(
                        schedule.id,
                        after=now,
                    )
                    continue

                job = await call_job_repository.create(client_id=schedule.client_id)
                await schedule_repository.mark_triggered(
                    schedule.id,
                    job_id=job.id,
                    triggered_at=now,
                )
                triggered_job_ids.append(job.id)

        for job_id in triggered_job_ids:
            if run_jobs:
                await self._call_job_service.run_job(job_id)
            logger.info("scheduled voice agent job triggered job_id=%s", job_id)

        return triggered_job_ids
