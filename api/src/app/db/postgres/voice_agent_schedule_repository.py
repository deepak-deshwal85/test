from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.postgres.models import ClientVoiceAgentScheduleRow
from app.domain.voice_agent_schedule_models import VoiceAgentSchedule
from app.services.voice_agent_schedule_time import (
    DEFAULT_DAYS_OF_WEEK,
    DEFAULT_RUN_TIME,
    DEFAULT_TIMEZONE,
    compute_next_run_at,
    deserialize_days_of_week,
    format_run_time,
    parse_days_of_week,
    parse_run_time,
    serialize_days_of_week,
)


class VoiceAgentScheduleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: ClientVoiceAgentScheduleRow) -> VoiceAgentSchedule:
        return VoiceAgentSchedule(
            id=row.id,
            client_id=row.client_id,
            enabled=row.enabled,
            run_time=row.run_time,
            days_of_week=deserialize_days_of_week(row.days_of_week),
            timezone=row.timezone,
            next_run_at=row.next_run_at,
            last_run_at=row.last_run_at,
            last_job_id=row.last_job_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def get_by_client_id(self, client_id: int) -> VoiceAgentSchedule | None:
        query = select(ClientVoiceAgentScheduleRow).where(
            ClientVoiceAgentScheduleRow.client_id == client_id
        )
        row = (await self._session.execute(query)).scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def get_or_create_default(self, client_id: int) -> VoiceAgentSchedule:
        existing = await self.get_by_client_id(client_id)
        if existing is not None:
            return existing

        row = ClientVoiceAgentScheduleRow(
            client_id=client_id,
            enabled=False,
            run_time=DEFAULT_RUN_TIME,
            days_of_week=serialize_days_of_week(DEFAULT_DAYS_OF_WEEK),
            timezone=DEFAULT_TIMEZONE,
            next_run_at=None,
        )
        self._session.add(row)
        try:
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise
        await self._session.refresh(row)
        return self._to_domain(row)

    async def upsert(
        self,
        *,
        client_id: int,
        enabled: bool,
        run_time: str,
        days_of_week: list[int],
        timezone: str,
    ) -> VoiceAgentSchedule:
        parsed_time = parse_run_time(run_time)
        parsed_days = parse_days_of_week(days_of_week)
        tz = timezone.strip()
        if not tz:
            raise ValueError("timezone is required")

        next_run_at = None
        if enabled:
            next_run_at = compute_next_run_at(
                run_time=parsed_time,
                days_of_week=parsed_days,
                timezone=tz,
            )

        row = (
            await self._session.execute(
                select(ClientVoiceAgentScheduleRow).where(
                    ClientVoiceAgentScheduleRow.client_id == client_id
                )
            )
        ).scalar_one_or_none()

        if row is None:
            row = ClientVoiceAgentScheduleRow(
                client_id=client_id,
                enabled=enabled,
                run_time=format_run_time(parsed_time),
                days_of_week=serialize_days_of_week(parsed_days),
                timezone=tz,
                next_run_at=next_run_at,
            )
            self._session.add(row)
        else:
            row.enabled = enabled
            row.run_time = format_run_time(parsed_time)
            row.days_of_week = serialize_days_of_week(parsed_days)
            row.timezone = tz
            row.next_run_at = next_run_at

        try:
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise
        await self._session.refresh(row)
        return self._to_domain(row)

    async def list_due(self, *, before: datetime) -> list[VoiceAgentSchedule]:
        query = (
            select(ClientVoiceAgentScheduleRow)
            .where(ClientVoiceAgentScheduleRow.enabled.is_(True))
            .where(ClientVoiceAgentScheduleRow.next_run_at.is_not(None))
            .where(ClientVoiceAgentScheduleRow.next_run_at <= before)
            .order_by(ClientVoiceAgentScheduleRow.next_run_at)
        )
        rows = (await self._session.execute(query)).scalars().all()
        return [self._to_domain(row) for row in rows]

    async def reschedule_next_run(
        self,
        schedule_id: int,
        *,
        after: datetime | None = None,
    ) -> VoiceAgentSchedule | None:
        row = await self._session.get(ClientVoiceAgentScheduleRow, schedule_id)
        if row is None:
            return None

        reference = after or datetime.now(UTC)
        if row.enabled:
            row.next_run_at = compute_next_run_at(
                run_time=parse_run_time(row.run_time),
                days_of_week=deserialize_days_of_week(row.days_of_week),
                timezone=row.timezone,
                after=reference,
            )
        else:
            row.next_run_at = None

        try:
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise
        await self._session.refresh(row)
        return self._to_domain(row)

    async def mark_triggered(
        self,
        schedule_id: int,
        *,
        job_id: UUID,
        triggered_at: datetime | None = None,
    ) -> VoiceAgentSchedule | None:
        row = await self._session.get(ClientVoiceAgentScheduleRow, schedule_id)
        if row is None:
            return None

        now = triggered_at or datetime.now(UTC)
        row.last_run_at = now
        row.last_job_id = job_id
        if row.enabled:
            row.next_run_at = compute_next_run_at(
                run_time=parse_run_time(row.run_time),
                days_of_week=deserialize_days_of_week(row.days_of_week),
                timezone=row.timezone,
                after=now,
            )
        else:
            row.next_run_at = None

        try:
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise
        await self._session.refresh(row)
        return self._to_domain(row)
