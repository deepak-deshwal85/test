from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Client:
    id: int
    client_phone_number: str
    client_name: str
    client_email_id: str
    cognito_sub: str | None
    created_at: datetime
