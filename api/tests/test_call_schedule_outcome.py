import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app.domain.consumer_status import (
    CONSUMER_STATUS_MEETING_NOT_SCHEDULED,
    CONSUMER_STATUS_MEETING_SCHEDULED,
    CONSUMER_STATUS_READY,
    consumer_status_after_call,
)
from app.schemas.call_summaries import CallSummaryCreateRequest
from app.schemas.consumers import ConsumerCreateRequest
from app.services.call_summary_service import CallSummaryService


def test_consumer_status_after_call():
    assert (
        consumer_status_after_call(meeting_scheduled=True)
        == CONSUMER_STATUS_MEETING_SCHEDULED
    )
    assert (
        consumer_status_after_call(meeting_scheduled=False)
        == CONSUMER_STATUS_MEETING_NOT_SCHEDULED
    )


@pytest.mark.asyncio
async def test_call_summary_create_updates_consumer_status():
    now = datetime.now(UTC)
    summary_repo = AsyncMock()
    consumer_repo = AsyncMock()
    service = CallSummaryService(summary_repo, consumer_repo)

    from app.domain.call_summary_models import CallSummary

    summary_repo.create.return_value = CallSummary(
        id=1,
        consumer_id=14,
        client_id=42,
        call_start_time=now,
        call_end_time=now,
        call_summary="Booked a meeting.",
        job_id=uuid4(),
        created_at=now,
        consumer_phone_number="919900000001",
        consumer_email_id="alice@example.com",
    )

    body = CallSummaryCreateRequest(
        consumer_id=14,
        call_start_time=now,
        call_end_time=now,
        call_summary="Booked a meeting.",
        meeting_scheduled=True,
    )
    await service.create(client_id=42, body=body)

    consumer_repo.update_status_after_call.assert_awaited_once_with(
        14,
        client_id=42,
        meeting_scheduled=True,
    )


def test_default_consumer_create_values():
    body = ConsumerCreateRequest(
        consumer_phone_number="919900000001",
        consumer_email_id="alice@example.com",
    )
    assert body.status == CONSUMER_STATUS_READY
