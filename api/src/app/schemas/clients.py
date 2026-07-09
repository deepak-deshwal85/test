from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ClientProfileResponse(BaseModel):
    id: int
    client_phone_number: str
    client_name: str
    client_email_id: str
    created_at: datetime


class ClientProfileUpsertRequest(BaseModel):
    client_name: str = Field(min_length=1, max_length=255)
    client_phone_number: str = Field(min_length=5, max_length=32)
    client_email_id: str = Field(min_length=3, max_length=255)
