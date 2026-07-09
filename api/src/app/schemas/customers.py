from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CustomerCreateRequest(BaseModel):
    client_phone_number: str = Field(min_length=1, max_length=32)
    client_name: str = Field(min_length=1, max_length=255)
    client_email_id: str = Field(min_length=3, max_length=255)
    consumer_phone_number: str = Field(min_length=1, max_length=32)
    consumer_email_id: str = Field(min_length=3, max_length=255)


class CustomerUpdateRequest(BaseModel):
    client_phone_number: str | None = Field(default=None, min_length=1, max_length=32)
    client_name: str | None = Field(default=None, min_length=1, max_length=255)
    client_email_id: str | None = Field(default=None, min_length=3, max_length=255)
    consumer_phone_number: str | None = Field(default=None, min_length=1, max_length=32)
    consumer_email_id: str | None = Field(default=None, min_length=3, max_length=255)


class CustomerResponse(BaseModel):
    id: int
    client_id: int | None
    client_phone_number: str
    client_name: str
    client_email_id: str
    consumer_phone_number: str
    consumer_email_id: str
    is_approved: bool
    created_at: datetime
    updated_at: datetime


class CustomerListResponse(BaseModel):
    customers: list[CustomerResponse]
    count: int
