import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from client_config import CalComConfig, ClientConfig
from scheduling_tools import build_scheduling_tools


@pytest.mark.asyncio
async def test_schedule_meeting_marks_call_outcome():
    config = ClientConfig(
        phone_number="911171366880",
        client_name="Acme Support",
        client_email_id="acme@example.com",
        greeting_message="Hello.",
        calcom=CalComConfig(
            username="acme-user",
            event_type_slug="30min",
            event_type_id=123,
        ),
    )
    call_outcome = {"meeting_scheduled": False}
    tools = build_scheduling_tools(
        config,
        default_timezone="Asia/Kolkata",
        call_outcome=call_outcome,
    )
    schedule_tool = next(tool for tool in tools if tool.id == "schedule_meeting")

    with patch(
        "scheduling_tools.book_meeting",
        new=AsyncMock(return_value="Meeting booked."),
    ):
        result = await schedule_tool(
            attendee_name="Alice",
            attendee_email="alice@example.com",
            meeting_date="2026-07-15",
            meeting_time="10:00",
        )

    assert result == "Meeting booked."
    assert call_outcome["meeting_scheduled"] is True
