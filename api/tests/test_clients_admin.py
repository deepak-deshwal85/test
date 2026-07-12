"""Tests for client onboarding admin endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient

from app.core.dependencies import get_client_service
from app.main import create_app
from app.schemas.clients import (
    ClientAdminListResponse,
    ClientAdminProfileResponse,
    ClientDeleteResponse,
)
from app.services.client_service import ClientService


@pytest.fixture
def rsa_keys():
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return private_key, public_key


def _encode_token(private_key, **claims) -> str:
    import time

    import jwt

    defaults = {
        "sub": "admin-123",
        "token_use": "access",
        "client_id": "ui-client-id",
        "scope": "relaydesk-api/access",
        "email": "admin@example.com",
        "iss": "https://cognito-idp.ap-south-1.amazonaws.com/ap-south-1_TestPool",
        "exp": int(time.time()) + 3600,
    }
    defaults.update(claims)
    return jwt.encode(
        defaults,
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )


def _install_fake_jwks(monkeypatch: pytest.MonkeyPatch, public_pem: bytes) -> None:
    from app.core import oauth as oauth_module

    class FakeSigningKey:
        key = public_pem

    class FakeJwkClient:
        def get_signing_key_from_jwt(self, _token):
            return FakeSigningKey()

    monkeypatch.setattr(oauth_module, "_jwks_client", lambda _url: FakeJwkClient())


@pytest.fixture(autouse=True)
def oauth_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OAUTH_DISABLED", "false")
    monkeypatch.setenv("COGNITO_REGION", "ap-south-1")
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "ap-south-1_TestPool")
    monkeypatch.setenv("COGNITO_UI_CLIENT_ID", "ui-client-id")
    monkeypatch.setenv("COGNITO_M2M_CLIENT_ID", "m2m-client-id")
    monkeypatch.setenv("COGNITO_REQUIRED_SCOPE", "relaydesk-api/access")
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_list_clients_admin_includes_approval_flag(
    monkeypatch: pytest.MonkeyPatch, rsa_keys
) -> None:
    private_key, public_key = rsa_keys
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    _install_fake_jwks(monkeypatch, public_pem)

    now = datetime.now(UTC)
    mock_service = AsyncMock(spec=ClientService)
    mock_service.list_clients_admin.return_value = ClientAdminListResponse(
        clients=[
            ClientAdminProfileResponse(
                id=1,
                client_phone_number=None,
                client_business_phone_number=None,
                client_name="Pending",
                client_email_id="pending@example.com",
                created_at=now,
                is_approved=False,
            )
        ],
        count=1,
    )

    app = create_app()
    app.dependency_overrides[get_client_service] = lambda: mock_service
    token = _encode_token(
        private_key,
        **{"cognito:groups": ["relaydesk-admins"]},
    )
    client = TestClient(app)
    response = client.get(
        "/v1/clients",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["clients"][0]["is_approved"] is False


def test_approve_client_requires_business_phone(
    monkeypatch: pytest.MonkeyPatch, rsa_keys
) -> None:
    private_key, public_key = rsa_keys
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    _install_fake_jwks(monkeypatch, public_pem)

    mock_service = AsyncMock(spec=ClientService)
    app = create_app()
    app.dependency_overrides[get_client_service] = lambda: mock_service
    token = _encode_token(
        private_key,
        **{"cognito:groups": ["relaydesk-admins"]},
    )
    client = TestClient(app)
    response = client.post(
        "/v1/clients/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "client_email_id": "pending@example.com",
        },
    )
    assert response.status_code == 422
    mock_service.approve_client.assert_not_awaited()


def test_approve_client_admin_only(
    monkeypatch: pytest.MonkeyPatch, rsa_keys
) -> None:
    private_key, public_key = rsa_keys
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    _install_fake_jwks(monkeypatch, public_pem)

    now = datetime.now(UTC)
    mock_service = AsyncMock(spec=ClientService)
    mock_service.approve_client.return_value = ClientAdminProfileResponse(
        id=1,
        client_phone_number=None,
        client_business_phone_number="911171366880",
        client_name="Approved",
        client_email_id="pending@example.com",
        created_at=now,
        is_approved=True,
    )

    app = create_app()
    app.dependency_overrides[get_client_service] = lambda: mock_service
    token = _encode_token(
        private_key,
        **{"cognito:groups": ["relaydesk-admins"]},
    )
    client = TestClient(app)
    response = client.post(
        "/v1/clients/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "client_email_id": "pending@example.com",
            "client_business_phone_number": "911171366880",
        },
    )
    assert response.status_code == 200
    assert response.json()["is_approved"] is True
    mock_service.approve_client.assert_awaited_once()


def test_approve_client_rejected_for_non_admin(
    monkeypatch: pytest.MonkeyPatch, rsa_keys
) -> None:
    private_key, public_key = rsa_keys
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    _install_fake_jwks(monkeypatch, public_pem)

    mock_service = AsyncMock(spec=ClientService)
    app = create_app()
    app.dependency_overrides[get_client_service] = lambda: mock_service
    token = _encode_token(
        private_key,
        email="user@example.com",
        **{"cognito:groups": ["approved-clients"]},
    )
    client = TestClient(app)
    response = client.post(
        "/v1/clients/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "client_email_id": "pending@example.com",
            "client_business_phone_number": "911171366880",
        },
    )
    assert response.status_code == 403


def test_delete_client_admin_success(
    monkeypatch: pytest.MonkeyPatch, rsa_keys
) -> None:
    private_key, public_key = rsa_keys
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    _install_fake_jwks(monkeypatch, public_pem)

    mock_service = AsyncMock(spec=ClientService)
    mock_service.delete_client.return_value = ClientDeleteResponse(
        client_email_id="client@example.com",
        deleted_consumers=3,
        deleted_call_jobs=2,
        qdrant_collection_deleted=True,
        cognito_user_deleted=True,
    )

    app = create_app()
    app.dependency_overrides[get_client_service] = lambda: mock_service
    token = _encode_token(
        private_key,
        **{"cognito:groups": ["relaydesk-admins"]},
    )
    client = TestClient(app)
    response = client.delete(
        "/v1/clients/account?client_email_id=client%40example.com",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["deleted_consumers"] == 3
    assert payload["deleted_call_jobs"] == 2
    assert payload["qdrant_collection_deleted"] is True
    assert payload["cognito_user_deleted"] is True
    mock_service.delete_client.assert_awaited_once_with("client@example.com")


def test_delete_client_not_found(
    monkeypatch: pytest.MonkeyPatch, rsa_keys
) -> None:
    private_key, public_key = rsa_keys
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    _install_fake_jwks(monkeypatch, public_pem)

    mock_service = AsyncMock(spec=ClientService)
    mock_service.delete_client.side_effect = ValueError("Client 'missing@example.com' not found")

    app = create_app()
    app.dependency_overrides[get_client_service] = lambda: mock_service
    token = _encode_token(
        private_key,
        **{"cognito:groups": ["relaydesk-admins"]},
    )
    client = TestClient(app)
    response = client.delete(
        "/v1/clients/account?client_email_id=missing%40example.com",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_delete_client_rejected_for_non_admin(
    monkeypatch: pytest.MonkeyPatch, rsa_keys
) -> None:
    private_key, public_key = rsa_keys
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    _install_fake_jwks(monkeypatch, public_pem)

    mock_service = AsyncMock(spec=ClientService)
    app = create_app()
    app.dependency_overrides[get_client_service] = lambda: mock_service
    token = _encode_token(
        private_key,
        email="user@example.com",
        **{"cognito:groups": ["approved-clients"]},
    )
    client = TestClient(app)
    response = client.delete(
        "/v1/clients/account?client_email_id=client%40example.com",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    mock_service.delete_client.assert_not_awaited()
