import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from calcom_client import CalComBookingResult, CalComClient
from client_config import CalComConfig
from meeting_scheduler import (
    MeetingRequest,
    book_meeting,
    format_available_slots,
    get_meeting_availability,
    normalize_spoken_email,
)
from scheduling_tools import build_meeting_scheduling_instructions


class FakeCalComClient(CalComClient):
    def __init__(
        self,
        *,
        slots: list[datetime] | None = None,
        booking_result: CalComBookingResult | None = None,
    ) -> None:
        super().__init__(api_key="cal_test")
        self._slots = slots or []
        self._booking_result = booking_result or CalComBookingResult(
            booking_uid="booking-123",
            start_utc=datetime(2026, 7, 1, 10, 0, tzinfo=UTC),
            meeting_url="https://meet.example.com/abc",
        )

    async def fetch_available_slots(self, *args, **kwargs) -> list[datetime]:
        return self._slots

    async def create_booking(self, *args, **kwargs) -> CalComBookingResult:
        return self._booking_result

    async def aclose(self) -> None:
        return None


CALCOM_CONFIG = CalComConfig(username="deepak", event_type_slug="30min")


def test_build_meeting_scheduling_instructions_mentions_tools():
    instructions = build_meeting_scheduling_instructions("Deepak Kumar")
    assert "schedule_meeting" in instructions
    assert "get_available_meeting_slots" in instructions


def test_format_available_slots_returns_plain_language():
    slots = [datetime(2026, 7, 1, 10, 0, tzinfo=UTC)]
    message = format_available_slots(slots, "Asia/Kolkata")
    assert message.startswith("Available times:")
    assert "2026" in message


def test_normalize_spoken_email():
    assert (
        normalize_spoken_email("deepakdeshwal85 at the rate of gmail dot com")
        == "deepakdeshwal85@gmail.com"
    )


@pytest.mark.asyncio
async def test_get_meeting_availability_uses_calcom_client():
    client = FakeCalComClient(
        slots=[datetime(2026, 7, 1, 10, 0, tzinfo=UTC)],
    )
    message = await get_meeting_availability(
        CALCOM_CONFIG,
        start_date="2026-07-01",
        end_date="2026-07-02",
        timezone="Asia/Kolkata",
        calcom_client=client,
    )
    assert "Available times:" in message


@pytest.mark.asyncio
async def test_book_meeting_creates_calcom_booking_and_audit_log(tmp_path: Path):
    meetings_file = tmp_path / "meetings.jsonl"
    slot = datetime(2026, 7, 1, 10, 0, tzinfo=UTC)
    client = FakeCalComClient(slots=[slot])
    request = MeetingRequest(
        client_phone_number="911171366880",
        client_name="Deepak Kumar",
        attendee_name="Jane Doe",
        attendee_email="jane@example.com",
        meeting_date="2026-07-01",
        meeting_time="15:30",
        timezone="Asia/Kolkata",
        notes="Phone screen",
    )

    confirmation = await book_meeting(
        request,
        CALCOM_CONFIG,
        meetings_file=meetings_file,
        now=datetime(2026, 6, 20, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata")),
        calcom_client=client,
    )

    assert "Jane Doe" in confirmation
    assert "calendar invite" in confirmation
    assert "https://meet.example.com/abc" in confirmation

    saved = [json.loads(line) for line in meetings_file.read_text(encoding="utf-8").splitlines()]
    assert saved[0]["calcom_booking_uid"] == "booking-123"


@pytest.mark.asyncio
async def test_book_meeting_rejects_unavailable_slot(tmp_path: Path):
    meetings_file = tmp_path / "meetings.jsonl"
    client = FakeCalComClient(slots=[datetime(2026, 7, 1, 11, 0, tzinfo=UTC)])
    request = MeetingRequest(
        client_phone_number="911171366880",
        client_name="Deepak Kumar",
        attendee_name="Jane Doe",
        attendee_email="jane@example.com",
        meeting_date="2026-07-01",
        meeting_time="15:30",
        timezone="Asia/Kolkata",
    )

    with pytest.raises(ValueError, match="not available"):
        await book_meeting(
            request,
            CALCOM_CONFIG,
            meetings_file=meetings_file,
            now=datetime(2026, 6, 20, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata")),
            calcom_client=client,
        )


@pytest.mark.asyncio
async def test_book_meeting_rejects_invalid_email(tmp_path: Path):
    meetings_file = tmp_path / "meetings.jsonl"
    client = FakeCalComClient(slots=[datetime(2026, 7, 1, 10, 0, tzinfo=UTC)])
    request = MeetingRequest(
        client_phone_number="911171366880",
        client_name="Deepak Kumar",
        attendee_name="Jane Doe",
        attendee_email="not-an-email",
        meeting_date="2026-07-01",
        meeting_time="15:30",
        timezone="Asia/Kolkata",
    )

    with pytest.raises(ValueError, match="email"):
        await book_meeting(
            request,
            CALCOM_CONFIG,
            meetings_file=meetings_file,
            calcom_client=client,
        )
