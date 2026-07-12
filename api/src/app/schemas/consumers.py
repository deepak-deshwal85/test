from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ConsumerStatusValue = Literal["READY", "MEETING_SCHEDULED", "MEETING_NOT_SCHEDULED"]


class ConsumerCreateRequest(BaseModel):
    consumer_phone_number: str = Field(min_length=1, max_length=32)
    consumer_email_id: str = Field(min_length=3, max_length=255)
    status: ConsumerStatusValue = "READY"


class ConsumerUpdateRequest(BaseModel):
    consumer_phone_number: str | None = Field(default=None, min_length=1, max_length=32)
    consumer_email_id: str | None = Field(default=None, min_length=3, max_length=255)
    status: ConsumerStatusValue | None = None


class ConsumerResponse(BaseModel):
    id: int
    client_id: int
    consumer_phone_number: str
    consumer_email_id: str
    is_approved: bool
    status: ConsumerStatusValue
    created_at: datetime
    updated_at: datetime


class ConsumerListResponse(BaseModel):
    consumers: list[ConsumerResponse]
    count: int
