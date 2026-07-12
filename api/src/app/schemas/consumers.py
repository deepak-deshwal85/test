from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CallScheduleValue = Literal["yes", "no"]
ConsumerStatusValue = Literal["READY", "MEETING_SCHEDULED", "MEETING_NOT_SCHEDULED"]


class ConsumerCreateRequest(BaseModel):
    client_business_phone_number: str = Field(min_length=1, max_length=32)
    client_name: str = Field(min_length=1, max_length=255)
    client_email_id: str = Field(min_length=3, max_length=255)
    consumer_phone_number: str = Field(min_length=1, max_length=32)
    consumer_email_id: str = Field(min_length=3, max_length=255)
    call_schedule: CallScheduleValue = "no"
    status: ConsumerStatusValue = "READY"


class ConsumerUpdateRequest(BaseModel):
    client_business_phone_number: str | None = Field(
        default=None, min_length=1, max_length=32
    )
    client_name: str | None = Field(default=None, min_length=1, max_length=255)
    client_email_id: str | None = Field(default=None, min_length=3, max_length=255)
    consumer_phone_number: str | None = Field(default=None, min_length=1, max_length=32)
    consumer_email_id: str | None = Field(default=None, min_length=3, max_length=255)
    call_schedule: CallScheduleValue | None = None
    status: ConsumerStatusValue | None = None


class ConsumerResponse(BaseModel):
    id: int
    client_id: int | None
    client_business_phone_number: str
    client_name: str
    client_email_id: str
    consumer_phone_number: str
    consumer_email_id: str
    is_approved: bool
    call_schedule: CallScheduleValue
    status: ConsumerStatusValue
    created_at: datetime
    updated_at: datetime


class ConsumerListResponse(BaseModel):
    consumers: list[ConsumerResponse]
    count: int
