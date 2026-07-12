import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app.core.dependencies import get_client_repository
from app.core.oauth import AuthenticatedPrincipal
from app.domain.client_models import Client
from app.main import create_app


def _m2m_principal() -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        subject="m2m-client",
        client_id="voice-agent",
        username=None,
        email=None,
        scopes=frozenset({"relaydesk-api/access"}),
        token_use="access",
        groups=frozenset(),
        role=None,
        is_m2m=True,
    )


@pytest.fixture
def mock_repository() -> AsyncMock:
    repository = AsyncMock()
    repository.get_by_business_phone.return_value = Client(
        id=1,
        client_phone_number=None,
        client_business_phone_number="91911171366880",
        client_name="Acme",
        client_email_id="client@example.com",
        created_at=datetime.now(UTC),
    )
    return repository


def test_resolve_by_phone_requires_m2m(mock_repository: AsyncMock) -> None:
    from app.core.dependencies import verify_access_token

    app = create_app()
    app.dependency_overrides[get_client_repository] = lambda: mock_repository

    async def _ui_user() -> AuthenticatedPrincipal:
        return AuthenticatedPrincipal(
            subject="user-1",
            client_id="ui",
            username=None,
            email="client@example.com",
            scopes=frozenset({"relaydesk-api/access"}),
            token_use="access",
            groups=frozenset({"approved-clients"}),
            role=None,
            is_m2m=False,
        )

    app.dependency_overrides[verify_access_token] = _ui_user
    client = TestClient(app)
    response = client.get(
        "/v1/clients/resolve-by-phone",
        params={"phone_number": "91911171366880"},
    )
    assert response.status_code == 403


def test_resolve_by_phone_returns_email(mock_repository: AsyncMock) -> None:
    from app.core.dependencies import verify_access_token

    app = create_app()
    app.dependency_overrides[get_client_repository] = lambda: mock_repository
    app.dependency_overrides[verify_access_token] = _m2m_principal
    client = TestClient(app)

    response = client.get(
        "/v1/clients/resolve-by-phone",
        params={"phone_number": "91911171366880"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["client_email_id"] == "client@example.com"
    assert data["collection_name"] == "client@example.com"
