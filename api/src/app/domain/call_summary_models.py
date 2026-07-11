from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CallSummary:
    id: int
    customer_id: int
    client_email_id: str
    call_start_time: datetime
    call_end_time: datetime | None
    call_summary: str
    job_id: uuid.UUID | None
    created_at: datetime
    consumer_phone_number: str | None = None
    consumer_email_id: str | None = None
