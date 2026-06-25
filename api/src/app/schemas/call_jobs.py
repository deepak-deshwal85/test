from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TriggerCallJobRequest(BaseModel):
    client_phone_number: str = Field(
        min_length=1,
        max_length=32,
        description="Client phone number whose consumers should be called",
    )


class CallJobResponse(BaseModel):
    id: UUID
    client_phone_number: str
    status: str
    total_customers: int
    calls_completed: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class TriggerCallJobResponse(BaseModel):
    job_id: UUID
    status: str
    message: str
