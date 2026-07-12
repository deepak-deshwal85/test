from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CallSummaryCreateRequest(BaseModel):
    consumer_id: int = Field(ge=1)
    call_start_time: datetime
    call_end_time: datetime | None = None
    call_summary: str = Field(default="", max_length=16000)
    job_id: UUID | None = None
    meeting_scheduled: bool = False


class CallSummaryUpdateRequest(BaseModel):
    call_start_time: datetime | None = None
    call_end_time: datetime | None = None
    call_summary: str | None = Field(default=None, max_length=16000)


class CallSummaryResponse(BaseModel):
    id: int
    consumer_id: int
    client_id: int
    call_start_time: datetime
    call_end_time: datetime | None
    call_summary: str
    job_id: UUID | None
    created_at: datetime
    consumer_phone_number: str | None = None
    consumer_email_id: str | None = None


class CallSummaryListResponse(BaseModel):
    summaries: list[CallSummaryResponse]
    count: int
