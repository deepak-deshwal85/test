import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app.core.dependencies import (
    get_call_job_service,
    get_client_repository,
    get_voice_agent_schedule_service,
    verify_access_token,
)
from app.core.oauth import AuthenticatedPrincipal
from app.main import create_app
from app.schemas.voice_agent_config import VoiceAgentConfigResponse
from app.schemas.voice_agent_schedules import (
    VoiceAgentScheduleOverviewResponse,
    VoiceAgentScheduleResponse,
    VoiceAgentScheduleTriggerResponse,
)


def _principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        subject="user-1",
        client_id="ui-client",
        username="acme@example.com",
        email="acme@example.com",
        scopes=frozenset({"relaydesk-api/access"}),
        token_use="access",
        groups=frozenset({"approved-clients"}),
        role="approved-clients",
        is_m2m=False,
    )


@pytest.fixture
def mock_service() -> AsyncMock:
    service = AsyncMock()
    now = datetime.now(UTC)
    config = VoiceAgentConfigResponse(
        id=1,
        client_id=10,
        client_email_id="acme@example.com",
        client_name="Acme Support",
        client_business_phone_number="911171366880",
        voice_agent_greeting_message="Hello from Acme.",
        calcom_username="acme-user",
        calcom_event_type_slug="30min",
        calcom_event_type_id=123,
        calcom_organization_slug=None,
        created_at=now,
        updated_at=now,
    )
    schedule = VoiceAgentScheduleResponse(
        id=1,
        client_id=10,
        enabled=True,
        run_time="09:00",
        days_of_week=[1, 2, 3, 4, 5],
        timezone="Asia/Kolkata",
        next_run_at=now,
        last_run_at=None,
        last_job_id=None,
        created_at=now,
        updated_at=now,
    )
    service.get_overview.return_value = VoiceAgentScheduleOverviewResponse(
        client_email_id="acme@example.com",
        client_name="Acme Support",
        client_business_phone_number="911171366880",
        ready_consumer_count=3,
        has_active_job=False,
        voice_agent_config=config,
        schedule=schedule,
    )
    service.update.return_value = service.get_overview.return_value
    job_id = uuid4()
    service.trigger_now.return_value = VoiceAgentScheduleTriggerResponse(
        job_id=job_id,
        status="pending",
        message="Campaign queued",
    )
    return service


def test_get_voice_agent_schedule(mock_service: AsyncMock) -> None:
    app = create_app()
    app.dependency_overrides[get_voice_agent_schedule_service] = lambda: mock_service
    app.dependency_overrides[get_client_repository] = lambda: AsyncMock()
    app.dependency_overrides[verify_access_token] = lambda: _principal()
    client = TestClient(app)

    response = client.get(
        "/v1/voice-agent-schedule?client_email_id=acme@example.com",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ready_consumer_count"] == 3
    assert body["schedule"]["enabled"] is True
    assert body["voice_agent_config"]["client_email_id"] == "acme@example.com"


def test_update_voice_agent_schedule(mock_service: AsyncMock) -> None:
    app = create_app()
    app.dependency_overrides[get_voice_agent_schedule_service] = lambda: mock_service
    app.dependency_overrides[get_client_repository] = lambda: AsyncMock()
    app.dependency_overrides[verify_access_token] = lambda: _principal()
    client = TestClient(app)

    response = client.put(
        "/v1/voice-agent-schedule?client_email_id=acme@example.com",
        json={
            "enabled": True,
            "run_time": "10:30",
            "days_of_week": [1, 3, 5],
            "timezone": "UTC",
        },
    )
    assert response.status_code == 200
    mock_service.update.assert_awaited_once()


def test_trigger_voice_agent_schedule(mock_service: AsyncMock) -> None:
    app = create_app()
    app.dependency_overrides[get_voice_agent_schedule_service] = lambda: mock_service
    app.dependency_overrides[get_call_job_service] = lambda: AsyncMock()
    app.dependency_overrides[get_client_repository] = lambda: AsyncMock()
    app.dependency_overrides[verify_access_token] = lambda: _principal()
    client = TestClient(app)

    response = client.post(
        "/v1/voice-agent-schedule/trigger?client_email_id=acme@example.com",
    )
    assert response.status_code == 202
    mock_service.trigger_now.assert_awaited_once()
