from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


from app.domain.phone_validation import (
    combine_phone_parts,
    normalize_optional_phone_number,
    normalize_phone_number,
)

__all__ = [
    "combine_phone_parts",
    "normalize_email",
    "normalize_optional_phone_number",
    "normalize_phone_number",
    "format_sip_phone",
    "Consumer",
    "CallJob",
    "CallAttemptResult",
]


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if "@" not in email:
        raise ValueError(f"Invalid email id: {value!r}")
    return email


def format_sip_phone(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("+"):
        return stripped
    digits = normalize_phone_number(stripped)
    if len(digits) == 10:
        return f"+91{digits}"
    return f"+{digits}"


@dataclass(frozen=True)
class Consumer:
    id: int
    client_id: int
    consumer_phone_number: str
    consumer_email_id: str
    is_approved: bool
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class CallJob:
    id: UUID
    client_id: int
    status: str
    total_consumers: int
    calls_completed: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    results: list[CallAttemptResult] | None = None


@dataclass(frozen=True)
class CallAttemptResult:
    consumer_id: int
    consumer_phone_number: str
    success: bool
    detail: str
