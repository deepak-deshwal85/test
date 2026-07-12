from __future__ import annotations

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

import pytest

from app.services.voice_agent_schedule_time import (
    compute_next_run_at,
    deserialize_days_of_week,
    parse_days_of_week,
    parse_run_time,
    serialize_days_of_week,
)


def test_parse_run_time_valid() -> None:
    assert parse_run_time("09:30") == time(9, 30)
    assert parse_run_time("23:59") == time(23, 59)


def test_parse_run_time_invalid() -> None:
    with pytest.raises(ValueError, match="HH:MM"):
        parse_run_time("9:30")
    with pytest.raises(ValueError, match="HH:MM"):
        parse_run_time("25:00")


def test_parse_days_of_week() -> None:
    assert parse_days_of_week([5, 1, 3]) == (1, 3, 5)
    with pytest.raises(ValueError):
        parse_days_of_week([])
    with pytest.raises(ValueError):
        parse_days_of_week([0])


def test_serialize_deserialize_days() -> None:
    raw = serialize_days_of_week((1, 3, 5))
    assert raw == "1,3,5"
    assert deserialize_days_of_week(raw) == (1, 3, 5)


def test_compute_next_run_at_same_day_later() -> None:
    tz = ZoneInfo("Asia/Kolkata")
    reference = datetime(2026, 7, 12, 8, 0, tzinfo=tz).astimezone(UTC)
    next_run = compute_next_run_at(
        run_time=time(9, 0),
        days_of_week=(7,),
        timezone="Asia/Kolkata",
        after=reference,
    )
    expected_local = datetime(2026, 7, 12, 9, 0, tzinfo=tz)
    assert next_run == expected_local.astimezone(UTC)


def test_compute_next_run_at_rolls_to_next_matching_day() -> None:
    tz = ZoneInfo("Asia/Kolkata")
    reference = datetime(2026, 7, 12, 10, 0, tzinfo=tz).astimezone(UTC)
    next_run = compute_next_run_at(
        run_time=time(9, 0),
        days_of_week=(1,),
        timezone="Asia/Kolkata",
        after=reference,
    )
    expected_local = datetime(2026, 7, 13, 9, 0, tzinfo=tz)
    assert next_run == expected_local.astimezone(UTC)
