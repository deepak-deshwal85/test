from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TriggerCallJobRequest(BaseModel):
    client_business_phone_number: str = Field(
        min_length=1,
        max_length=32,
        description="Client business phone number whose consumers should be called",
    )
    client_email_id: str = Field(min_length=3, max_length=255)


class CallAttemptResponse(BaseModel):
    consumer_id: int
    consumer_phone_number: str
    success: bool
    detail: str


class CallJobResponse(BaseModel):
    id: UUID
    client_business_phone_number: str
    client_email_id: str
    status: str
    total_consumers: int
    calls_completed: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    results: list[CallAttemptResponse] | None = None


class TriggerCallJobResponse(BaseModel):
    job_id: UUID
    status: str
    message: str


class CallJobListResponse(BaseModel):
    jobs: list[CallJobResponse]
    count: int
