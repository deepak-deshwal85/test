from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Client:
    id: int
    client_phone_number: str | None
    client_business_phone_number: str | None
    client_name: str
    client_email_id: str
    created_at: datetime
