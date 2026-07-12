from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.voice_agent_config import VoiceAgentConfigResponse


class VoiceAgentScheduleResponse(BaseModel):
    id: int
    client_id: int
    enabled: bool
    run_time: str
    days_of_week: list[int]
    timezone: str
    next_run_at: datetime | None
    last_run_at: datetime | None
    last_job_id: UUID | None
    created_at: datetime
    updated_at: datetime


class VoiceAgentScheduleUpdateRequest(BaseModel):
    enabled: bool = False
    run_time: str = Field(default="09:00", pattern=r"^([01]\d|2[0-3]):([0-5]\d)$")
    days_of_week: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5])
    timezone: str = Field(default="Asia/Kolkata", min_length=1, max_length=64)

    @field_validator("days_of_week")
    @classmethod
    def validate_days(cls, values: list[int]) -> list[int]:
        if not values:
            raise ValueError("days_of_week must include at least one day")
        for day in values:
            if day < 1 or day > 7:
                raise ValueError("days_of_week values must be between 1 and 7")
        return sorted(set(values))


class VoiceAgentScheduleOverviewResponse(BaseModel):
    client_email_id: str
    client_name: str
    client_business_phone_number: str | None
    ready_consumer_count: int
    has_active_job: bool
    voice_agent_config: VoiceAgentConfigResponse
    schedule: VoiceAgentScheduleResponse


class VoiceAgentScheduleTriggerResponse(BaseModel):
    job_id: UUID
    status: str
    message: str
