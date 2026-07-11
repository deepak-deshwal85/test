import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app.domain.customer_status import (
    CUSTOMER_STATUS_MEETING_NOT_SCHEDULED,
    CUSTOMER_STATUS_MEETING_SCHEDULED,
    CUSTOMER_STATUS_READY,
    customer_status_after_call,
)
from app.schemas.call_summaries import CallSummaryCreateRequest
from app.schemas.customers import CustomerCreateRequest
from app.services.call_summary_service import CallSummaryService


def test_customer_status_after_call():
    assert (
        customer_status_after_call(meeting_scheduled=True)
        == CUSTOMER_STATUS_MEETING_SCHEDULED
    )
    assert (
        customer_status_after_call(meeting_scheduled=False)
        == CUSTOMER_STATUS_MEETING_NOT_SCHEDULED
    )


@pytest.mark.asyncio
async def test_call_summary_create_updates_customer_status():
    now = datetime.now(UTC)
    summary_repo = AsyncMock()
    customer_repo = AsyncMock()
    service = CallSummaryService(summary_repo, customer_repo)

    from app.domain.call_summary_models import CallSummary

    summary_repo.create.return_value = CallSummary(
        id=1,
        customer_id=14,
        client_email_id="acme@example.com",
        call_start_time=now,
        call_end_time=now,
        call_summary="Booked a meeting.",
        job_id=uuid4(),
        created_at=now,
        consumer_phone_number="919900000001",
        consumer_email_id="alice@example.com",
    )

    body = CallSummaryCreateRequest(
        customer_id=14,
        call_start_time=now,
        call_end_time=now,
        call_summary="Booked a meeting.",
        meeting_scheduled=True,
    )
    await service.create(client_email_id="acme@example.com", body=body)

    customer_repo.update_status_after_call.assert_awaited_once_with(
        14,
        client_email_id="acme@example.com",
        meeting_scheduled=True,
    )


def test_default_customer_create_values():
    body = CustomerCreateRequest(
        client_business_phone_number="911171366880",
        client_name="Acme",
        client_email_id="acme@example.com",
        consumer_phone_number="919900000001",
        consumer_email_id="alice@example.com",
    )
    assert body.call_schedule == "no"
    assert body.status == CUSTOMER_STATUS_READY
