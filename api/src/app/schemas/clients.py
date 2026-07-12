from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.domain.phone_validation import (
    normalize_optional_phone_number,
    normalize_phone_number,
)


class ClientProfileResponse(BaseModel):
    id: int
    client_phone_number: str | None
    client_business_phone_number: str | None
    client_name: str
    client_email_id: str
    created_at: datetime


class ClientAdminProfileResponse(ClientProfileResponse):
    is_approved: bool


class ClientProfileUpsertRequest(BaseModel):
    client_name: str = Field(min_length=1, max_length=255)
    client_phone_number: str | None = Field(default=None, min_length=5, max_length=32)

    @field_validator("client_phone_number")
    @classmethod
    def validate_personal_phone(cls, value: str | None) -> str | None:
        return normalize_optional_phone_number(value)


class ClientApproveRequest(BaseModel):
    client_email_id: str = Field(min_length=3, max_length=255)
    client_business_phone_number: str = Field(min_length=5, max_length=32)

    @field_validator("client_business_phone_number")
    @classmethod
    def validate_business_phone(cls, value: str) -> str:
        return normalize_phone_number(value)


class ClientListResponse(BaseModel):
    clients: list[ClientProfileResponse]
    count: int


class ClientAdminListResponse(BaseModel):
    clients: list[ClientAdminProfileResponse]
    count: int


class ClientDeleteResponse(BaseModel):
    client_email_id: str
    deleted_consumers: int
    deleted_call_jobs: int
    qdrant_collection_deleted: bool
    cognito_user_deleted: bool
