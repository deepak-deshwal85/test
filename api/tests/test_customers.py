import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app.main import create_app
from app.schemas.call_jobs import CallJobResponse
from app.schemas.customers import CustomerResponse


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_customer(client: TestClient) -> None:
    from unittest.mock import AsyncMock

    from app.core.dependencies import get_client_repository, get_customer_service

    now = datetime.now(UTC)
    mock_service = AsyncMock()
    mock_service.create.return_value = CustomerResponse(
        id=1,
        client_id=None,
        client_business_phone_number="911171366880",
        client_name="Acme Corp",
        client_email_id="acme@example.com",
        consumer_phone_number="9876543210",
        consumer_email_id="consumer@example.com",
        is_approved=False,
        call_schedule="no",
        status="active",
        created_at=now,
        updated_at=now,
    )
    mock_repository = AsyncMock()
    mock_repository.get_by_email.return_value = None
    mock_repository.get_by_cognito_sub.return_value = None

    app = create_app()
    app.dependency_overrides[get_customer_service] = lambda: mock_service
    app.dependency_overrides[get_client_repository] = lambda: mock_repository
    test_client = TestClient(app)

    response = test_client.post(
        "/v1/customers",
        json={
            "client_business_phone_number": "911171366880",
            "client_name": "Acme Corp",
            "client_email_id": "acme@example.com",
            "consumer_phone_number": "9876543210",
            "consumer_email_id": "consumer@example.com",
        },
    )
    assert response.status_code == 201
    assert response.json()["client_name"] == "Acme Corp"


def test_trigger_call_job(client: TestClient) -> None:
    from app.core.dependencies import get_call_job_service, get_client_repository

    job_id = uuid4()
    now = datetime.now(UTC)
    mock_service = AsyncMock()
    mock_service.create_job.return_value = CallJobResponse(
        id=job_id,
        client_business_phone_number="911171366880",
        client_email_id="acme@example.com",
        status="pending",
        total_customers=0,
        calls_completed=0,
        error_message=None,
        started_at=None,
        completed_at=None,
        created_at=now,
    )
    mock_service.run_job = AsyncMock()
    mock_repository = AsyncMock()
    mock_repository.get_by_email.return_value = None
    mock_repository.get_by_cognito_sub.return_value = None

    app = create_app()
    app.dependency_overrides[get_call_job_service] = lambda: mock_service
    app.dependency_overrides[get_client_repository] = lambda: mock_repository
    test_client = TestClient(app)

    response = test_client.post(
        "/v1/call-jobs/trigger",
        json={
            "client_business_phone_number": "911171366880",
            "client_email_id": "acme@example.com",
        },
    )
    assert response.status_code == 202
    data = response.json()
    assert data["job_id"] == str(job_id)
    assert data["status"] == "pending"


def test_raise_from_integrity_error_maps_not_null() -> None:
    from sqlalchemy.exc import IntegrityError

    from app.db.postgres.customer_repository import _raise_from_integrity_error

    exc = IntegrityError("INSERT", {}, Exception('null value in column "client_phone_number"'))
    try:
        _raise_from_integrity_error(exc)
    except ValueError as err:
        assert "schema migrations" in str(err)
    else:
        raise AssertionError("expected ValueError")


def test_raise_from_integrity_error_maps_unique() -> None:
    from sqlalchemy.exc import IntegrityError

    from app.db.postgres.customer_repository import _raise_from_integrity_error

    exc = IntegrityError("INSERT", {}, Exception("duplicate key value violates unique constraint"))
    try:
        _raise_from_integrity_error(exc)
    except ValueError as err:
        assert "already exists" in str(err)
    else:
        raise AssertionError("expected ValueError")
    from app.domain.customer_models import normalize_phone_number

    assert normalize_phone_number("+91 91117 1366880") == "91911171366880"
    assert normalize_phone_number("9876543210") == "9876543210"


def test_create_customer_rejects_duplicate(client: TestClient) -> None:
    from unittest.mock import AsyncMock

    from app.core.dependencies import get_client_repository, get_customer_service

    mock_service = AsyncMock()
    mock_service.create.side_effect = ValueError(
        "Customer already exists for this client and consumer phone number"
    )
    mock_repository = AsyncMock()
    mock_repository.get_by_email.return_value = None
    mock_repository.get_by_cognito_sub.return_value = None

    app = create_app()
    app.dependency_overrides[get_customer_service] = lambda: mock_service
    app.dependency_overrides[get_client_repository] = lambda: mock_repository
    test_client = TestClient(app)

    response = test_client.post(
        "/v1/customers",
        json={
            "client_business_phone_number": "911171366880",
            "client_name": "Acme Corp",
            "client_email_id": "acme@example.com",
            "consumer_phone_number": "9876543210",
            "consumer_email_id": "consumer@example.com",
        },
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_create_customer_rejects_consumer_matching_business_phone(
    client: TestClient,
) -> None:
    from unittest.mock import AsyncMock

    from app.core.dependencies import get_client_repository, get_customer_service

    mock_service = AsyncMock()
    mock_service.create.side_effect = ValueError(
        "Consumer phone number must be different from the client business phone"
    )
    mock_repository = AsyncMock()
    mock_repository.get_by_email.return_value = None
    mock_repository.get_by_cognito_sub.return_value = None

    app = create_app()
    app.dependency_overrides[get_customer_service] = lambda: mock_service
    app.dependency_overrides[get_client_repository] = lambda: mock_repository
    test_client = TestClient(app)

    response = test_client.post(
        "/v1/customers",
        json={
            "client_business_phone_number": "911171366880",
            "client_name": "Acme Corp",
            "client_email_id": "acme@example.com",
            "consumer_phone_number": "911171366880",
            "consumer_email_id": "consumer@example.com",
        },
    )
    assert response.status_code == 400
    assert "different from the client business phone" in response.json()["detail"]
