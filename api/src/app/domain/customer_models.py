from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


def normalize_phone_number(value: str) -> str:
    digits = "".join(character for character in value if character.isdigit())
    if not digits:
        raise ValueError(f"Invalid phone number: {value!r}")
    return digits


def format_sip_phone(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("+"):
        return stripped
    digits = normalize_phone_number(stripped)
    if len(digits) == 10:
        return f"+91{digits}"
    return f"+{digits}"


@dataclass(frozen=True)
class Customer:
    id: int
    client_phone_number: str
    client_name: str
    consumer_phone_number: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class CallJob:
    id: UUID
    client_phone_number: str
    status: str
    total_customers: int
    calls_completed: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    results: list[CallAttemptResult] | None = None


@dataclass(frozen=True)
class CallAttemptResult:
    customer_id: int
    consumer_phone_number: str
    success: bool
    detail: str
