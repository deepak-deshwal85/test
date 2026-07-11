import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app.main import create_app
from app.schemas.call_summaries import CallSummaryResponse


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_create_call_summary(client: TestClient) -> None:
    from app.core.dependencies import (
        get_call_summary_service,
        get_client_repository,
        get_customer_service,
    )

    now = datetime.now(UTC)
    job_id = uuid4()
    mock_service = AsyncMock()
    mock_service.create.return_value = CallSummaryResponse(
        id=1,
        customer_id=14,
        client_email_id="acme@example.com",
        call_start_time=now,
        call_end_time=now,
        call_summary="Caller asked about pricing.",
        job_id=job_id,
        created_at=now,
        consumer_phone_number="919900000001",
        consumer_email_id="alice.consumer@example.com",
    )
    mock_customer_service = AsyncMock()
    mock_customer_service.get.return_value = type(
        "CustomerStub",
        (),
        {"client_email_id": "acme@example.com"},
    )()
    mock_repository = AsyncMock()

    app = create_app()
    app.dependency_overrides[get_call_summary_service] = lambda: mock_service
    app.dependency_overrides[get_customer_service] = lambda: mock_customer_service
    app.dependency_overrides[get_client_repository] = lambda: mock_repository
    test_client = TestClient(app)

    response = test_client.post(
        "/v1/call-summaries?client_email_id=acme@example.com",
        json={
            "customer_id": 14,
            "call_start_time": now.isoformat(),
            "call_end_time": now.isoformat(),
            "call_summary": "Caller asked about pricing.",
            "job_id": str(job_id),
        },
    )
    assert response.status_code == 201
    assert response.json()["customer_id"] == 14


def test_list_call_summaries(client: TestClient) -> None:
    from app.core.dependencies import get_call_summary_service, get_client_repository

    now = datetime.now(UTC)
    mock_service = AsyncMock()
    mock_service.list.return_value = [
        CallSummaryResponse(
            id=1,
            customer_id=14,
            client_email_id="acme@example.com",
            call_start_time=now,
            call_end_time=now,
            call_summary="Summary text",
            job_id=None,
            created_at=now,
            consumer_phone_number="919900000001",
            consumer_email_id="alice.consumer@example.com",
        )
    ]
    mock_repository = AsyncMock()

    app = create_app()
    app.dependency_overrides[get_call_summary_service] = lambda: mock_service
    app.dependency_overrides[get_client_repository] = lambda: mock_repository
    test_client = TestClient(app)

    response = test_client.get(
        "/v1/call-summaries?client_email_id=acme@example.com"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["summaries"][0]["call_summary"] == "Summary text"
