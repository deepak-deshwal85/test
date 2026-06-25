from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CustomerCreateRequest(BaseModel):
    client_phone_number: str = Field(min_length=1, max_length=32)
    client_name: str = Field(min_length=1, max_length=255)
    consumer_phone_number: str = Field(min_length=1, max_length=32)


class CustomerUpdateRequest(BaseModel):
    client_phone_number: str | None = Field(default=None, min_length=1, max_length=32)
    client_name: str | None = Field(default=None, min_length=1, max_length=255)
    consumer_phone_number: str | None = Field(default=None, min_length=1, max_length=32)


class CustomerResponse(BaseModel):
    id: int
    client_phone_number: str
    client_name: str
    consumer_phone_number: str
    created_at: datetime
    updated_at: datetime


class CustomerListResponse(BaseModel):
    customers: list[CustomerResponse]
    count: int
