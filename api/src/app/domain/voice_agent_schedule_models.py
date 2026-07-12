from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class VoiceAgentSchedule:
    id: int
    client_id: int
    enabled: bool
    run_time: str
    days_of_week: tuple[int, ...]
    timezone: str
    next_run_at: datetime | None
    last_run_at: datetime | None
    last_job_id: UUID | None
    created_at: datetime
    updated_at: datetime
