from __future__ import annotations

import re
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

RUN_TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
DEFAULT_DAYS_OF_WEEK = (1, 2, 3, 4, 5)
DEFAULT_RUN_TIME = "09:00"
DEFAULT_TIMEZONE = "Asia/Kolkata"


def parse_run_time(value: str) -> time:
    normalized = value.strip()
    match = RUN_TIME_PATTERN.match(normalized)
    if not match:
        raise ValueError("run_time must be HH:MM in 24-hour format")
    return time(hour=int(match.group(1)), minute=int(match.group(2)))


def format_run_time(value: time) -> str:
    return value.strftime("%H:%M")


def parse_days_of_week(values: list[int]) -> tuple[int, ...]:
    if not values:
        raise ValueError("days_of_week must include at least one day")
    normalized: list[int] = []
    for day in values:
        if day < 1 or day > 7:
            raise ValueError("days_of_week values must be between 1 (Mon) and 7 (Sun)")
        if day not in normalized:
            normalized.append(day)
    return tuple(sorted(normalized))


def serialize_days_of_week(days: tuple[int, ...]) -> str:
    return ",".join(str(day) for day in days)


def deserialize_days_of_week(raw: str) -> tuple[int, ...]:
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    if not parts:
        return DEFAULT_DAYS_OF_WEEK
    return parse_days_of_week([int(part) for part in parts])


def compute_next_run_at(
    *,
    run_time: time,
    days_of_week: tuple[int, ...],
    timezone: str,
    after: datetime | None = None,
) -> datetime:
    tz = ZoneInfo(timezone)
    reference = (after or datetime.now(UTC)).astimezone(tz)
    for offset in range(0, 14):
        candidate_date = reference.date() + timedelta(days=offset)
        if candidate_date.isoweekday() not in days_of_week:
            continue
        candidate = datetime.combine(candidate_date, run_time, tzinfo=tz)
        if candidate > reference:
            return candidate.astimezone(UTC)
    raise ValueError("Could not compute next_run_at within 14 days")
