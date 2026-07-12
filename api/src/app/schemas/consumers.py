from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.domain.phone_validation import normalize_phone_number

ConsumerStatusValue = Literal["READY", "MEETING_SCHEDULED", "MEETING_NOT_SCHEDULED"]


def _validate_phone_field(value: str) -> str:
    return normalize_phone_number(value)


class ConsumerCreateRequest(BaseModel):
    consumer_phone_number: str = Field(min_length=1, max_length=32)
    consumer_email_id: str = Field(min_length=3, max_length=255)
    consumer_name: str = Field(default="", max_length=255)
    consumer_address: str = Field(default="", max_length=2000)
    status: ConsumerStatusValue = "READY"

    @field_validator("consumer_phone_number")
    @classmethod
    def validate_consumer_phone(cls, value: str) -> str:
        return _validate_phone_field(value)


class ConsumerUpdateRequest(BaseModel):
    consumer_phone_number: str | None = Field(default=None, min_length=1, max_length=32)
    consumer_email_id: str | None = Field(default=None, min_length=3, max_length=255)
    consumer_name: str | None = Field(default=None, max_length=255)
    consumer_address: str | None = Field(default=None, max_length=2000)
    status: ConsumerStatusValue | None = None

    @field_validator("consumer_phone_number")
    @classmethod
    def validate_consumer_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_phone_field(value)


class ConsumerResponse(BaseModel):
    id: int
    client_id: int
    consumer_phone_number: str
    consumer_email_id: str
    consumer_name: str = ""
    consumer_address: str = ""
    is_approved: bool
    status: ConsumerStatusValue
    created_at: datetime
    updated_at: datetime


class ConsumerListResponse(BaseModel):
    consumers: list[ConsumerResponse]
    count: int
