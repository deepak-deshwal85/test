from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ClientProfileResponse(BaseModel):
    id: int
    client_phone_number: str | None
    client_business_phone_number: str | None
    client_name: str
    client_email_id: str
    created_at: datetime


class ClientAdminProfileResponse(ClientProfileResponse):
    is_approved: bool
    cognito_sub: str | None = None


class ClientProfileUpsertRequest(BaseModel):
    client_name: str = Field(min_length=1, max_length=255)
    client_phone_number: str | None = Field(default=None, min_length=5, max_length=32)


class ClientApproveRequest(BaseModel):
    client_email_id: str = Field(min_length=3, max_length=255)
    client_business_phone_number: str = Field(min_length=5, max_length=32)


class ClientListResponse(BaseModel):
    clients: list[ClientProfileResponse]
    count: int


class ClientAdminListResponse(BaseModel):
    clients: list[ClientAdminProfileResponse]
    count: int
