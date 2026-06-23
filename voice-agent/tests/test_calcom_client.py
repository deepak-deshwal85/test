import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from calcom_client import CalComClient, CalComError, CalComEventConfig


@pytest.mark.asyncio
async def test_fetch_available_slots_parses_response():
    config = CalComEventConfig(username="deepak", event_type_slug="30min")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/slots"
        assert request.url.params["username"] == "deepak"
        assert request.url.params["eventTypeSlug"] == "30min"
        return httpx.Response(
            200,
            json={
                "data": {
                    "slots": {
                        "2026-07-01": [
                            {"time": "2026-07-01T10:00:00Z"},
                            {"time": "2026-07-01T11:00:00Z"},
                        ]
                    }
                }
            },
        )

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(
        transport=transport,
        base_url="https://api.cal.com",
    )
    client = CalComClient(api_key="cal_test", http_client=http_client)

    slots = await client.fetch_available_slots(
        config,
        start_date="2026-07-01",
        end_date="2026-07-02",
        timezone="Asia/Kolkata",
    )

    assert len(slots) == 2
    assert slots[0] == datetime(2026, 7, 1, 10, 0, tzinfo=UTC)
    await client.aclose()


@pytest.mark.asyncio
async def test_fetch_available_slots_parses_date_key_response():
    config = CalComEventConfig(
        username="deepak",
        event_type_slug="30min",
        event_type_id=6073963,
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["eventTypeId"] == "6073963"
        return httpx.Response(
            200,
            json={
                "data": {
                    "2026-07-01": [
                        {"start": "2026-07-01T10:00:00.000+05:30"},
                        {"start": "2026-07-01T11:00:00.000+05:30"},
                    ]
                }
            },
        )

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(
        transport=transport,
        base_url="https://api.cal.com",
    )
    client = CalComClient(api_key="cal_test", http_client=http_client)

    slots = await client.fetch_available_slots(
        config,
        start_date="2026-07-01",
        end_date="2026-07-02",
        timezone="Asia/Kolkata",
    )

    assert len(slots) == 2
    assert slots[0] == datetime(2026, 7, 1, 4, 30, tzinfo=UTC)
    await client.aclose()


@pytest.mark.asyncio
async def test_create_booking_sends_expected_payload():
    config = CalComEventConfig(username="deepak", event_type_slug="30min")
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["json"] = request.content.decode("utf-8")
        return httpx.Response(
            201,
            json={
                "data": {
                    "uid": "booking-123",
                    "start": "2026-07-01T10:00:00Z",
                    "meetingUrl": "https://meet.example.com/abc",
                }
            },
        )

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(
        transport=transport,
        base_url="https://api.cal.com",
    )
    client = CalComClient(api_key="cal_test", http_client=http_client)

    result = await client.create_booking(
        config,
        start_utc=datetime(2026, 7, 1, 10, 0, tzinfo=UTC),
        attendee_name="Jane Doe",
        attendee_email="jane@example.com",
        timezone="Asia/Kolkata",
        notes="Phone screen",
    )

    assert result.booking_uid == "booking-123"
    assert result.meeting_url == "https://meet.example.com/abc"
    assert '"username":"deepak"' in captured["json"]
    assert '"eventTypeSlug":"30min"' in captured["json"]
    await client.aclose()


@pytest.mark.asyncio
async def test_create_booking_raises_on_api_error():
    config = CalComEventConfig(username="deepak", event_type_slug="30min")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": {"message": "Slot no longer available"}},
        )

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(
        transport=transport,
        base_url="https://api.cal.com",
    )
    client = CalComClient(http_client=http_client)

    with pytest.raises(CalComError, match="Slot no longer available"):
        await client.create_booking(
            config,
            start_utc=datetime(2026, 7, 1, 10, 0, tzinfo=UTC),
            attendee_name="Jane Doe",
            attendee_email="jane@example.com",
            timezone="Asia/Kolkata",
        )
    await client.aclose()
