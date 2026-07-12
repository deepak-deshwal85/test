import pytest

from app.core.config import get_settings


@pytest.fixture
def mock_client_repository():
    from datetime import UTC, datetime
    from unittest.mock import AsyncMock

    from app.domain.client_models import Client

    repository = AsyncMock()
    repository.get_by_email.return_value = Client(
        id=1,
        client_phone_number=None,
        client_business_phone_number="911171366880",
        client_name="Test Client",
        client_email_id="user@example.com",
        cognito_sub="user-123",
        created_at=datetime.now(UTC),
    )
    repository.get_by_cognito_sub.return_value = None
    repository.get_by_business_phone.return_value = repository.get_by_email.return_value
    return repository


@pytest.fixture(autouse=True)
def oauth_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OAUTH_DISABLED", "false")
    monkeypatch.setenv("COGNITO_REGION", "ap-south-1")
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "ap-south-1_TestPool")
    monkeypatch.setenv("COGNITO_UI_CLIENT_ID", "ui-client-id")
    monkeypatch.setenv("COGNITO_M2M_CLIENT_ID", "m2m-client-id")
    monkeypatch.setenv("COGNITO_REQUIRED_SCOPE", "relaydesk-api/access")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


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
        "sub": "user-123",
        "token_use": "access",
        "client_id": "ui-client-id",
        "scope": "relaydesk-api/access",
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


def test_protected_route_requires_bearer(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from app.core import oauth as oauth_module
    from app.main import create_app

    monkeypatch.setattr(oauth_module, "_jwks_client", lambda _url: None)
    client = TestClient(create_app())
    response = client.post(
        "/v1/search",
        json={"phone_number": "911171366880", "query": "hi"},
    )
    assert response.status_code == 401


def test_guest_client_can_read(
    monkeypatch: pytest.MonkeyPatch, rsa_keys, mock_client_repository
) -> None:
    from cryptography.hazmat.primitives import serialization
    from fastapi.testclient import TestClient
    from unittest.mock import MagicMock

    from app.core.dependencies import get_client_repository, get_search_service
    from app.main import create_app

    private_key, public_key = rsa_keys
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    _install_fake_jwks(monkeypatch, public_pem)

    mock_service = MagicMock()
    mock_service.search.return_value = ([], "user@example.com")

    app = create_app()
    app.dependency_overrides[get_search_service] = lambda: mock_service
    app.dependency_overrides[get_client_repository] = lambda: mock_client_repository
    token = _encode_token(
        private_key,
        email="user@example.com",
        **{"cognito:groups": ["guest-clients"]},
    )
    client = TestClient(app)
    response = client.post(
        "/v1/search",
        json={
            "query": "hello",
            "client_email_id": "user@example.com",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_user_without_role_gets_guest_read_access(
    monkeypatch: pytest.MonkeyPatch, rsa_keys, mock_client_repository
) -> None:
    from cryptography.hazmat.primitives import serialization
    from fastapi.testclient import TestClient
    from unittest.mock import MagicMock

    from app.core.dependencies import get_client_repository, get_search_service
    from app.main import create_app

    private_key, public_key = rsa_keys
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    _install_fake_jwks(monkeypatch, public_pem)

    mock_service = MagicMock()
    mock_service.search.return_value = ([], "user@example.com")

    app = create_app()
    app.dependency_overrides[get_search_service] = lambda: mock_service
    app.dependency_overrides[get_client_repository] = lambda: mock_client_repository
    token = _encode_token(
        private_key,
        client_id="ui-client-id",
        email="user@example.com",
    )
    client = TestClient(app)
    response = client.post(
        "/v1/search",
        json={
            "query": "hello",
            "client_email_id": "user@example.com",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_guest_cannot_upload_documents(
    monkeypatch: pytest.MonkeyPatch, rsa_keys, mock_client_repository
) -> None:
    from cryptography.hazmat.primitives import serialization
    from fastapi.testclient import TestClient

    from app.core.dependencies import get_client_repository
    from app.main import create_app

    private_key, public_key = rsa_keys
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    _install_fake_jwks(monkeypatch, public_pem)

    app = create_app()
    app.dependency_overrides[get_client_repository] = lambda: mock_client_repository
    token = _encode_token(
        private_key,
        email="user@example.com",
        **{"cognito:groups": ["guest-clients"]},
    )
    client = TestClient(app)
    response = client.post(
        "/v1/collections/user@example.com/documents/upload"
        "?client_email_id=user%40example.com",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient permissions"


def test_approved_client_can_upload_documents(
    monkeypatch: pytest.MonkeyPatch, rsa_keys, mock_client_repository
) -> None:
    from cryptography.hazmat.primitives import serialization
    from fastapi.testclient import TestClient
    from unittest.mock import MagicMock

    from app.core.dependencies import get_client_repository, get_document_service
    from app.domain.models import IngestResult
    from app.main import create_app

    private_key, public_key = rsa_keys
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    _install_fake_jwks(monkeypatch, public_pem)

    mock_service = MagicMock()
    mock_service.ingest_upload.return_value = IngestResult(
        collection="user@example.com",
        document_id="doc-1",
        source_uri="notes.txt",
        chunks_indexed=1,
    )

    app = create_app()
    app.dependency_overrides[get_document_service] = lambda: mock_service
    app.dependency_overrides[get_client_repository] = lambda: mock_client_repository
    token = _encode_token(
        private_key,
        email="user@example.com",
        **{"cognito:groups": ["approved-clients"]},
    )
    client = TestClient(app)
    response = client.post(
        "/v1/collections/user@example.com/documents/upload"
        "?client_email_id=user%40example.com",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 200


def test_approved_client_can_create_consumers(
    monkeypatch: pytest.MonkeyPatch, rsa_keys, mock_client_repository
) -> None:
    from datetime import UTC, datetime
    from cryptography.hazmat.primitives import serialization
    from fastapi.testclient import TestClient
    from unittest.mock import AsyncMock

    from app.core.dependencies import get_client_repository, get_consumer_service
    from app.main import create_app
    from app.schemas.consumers import ConsumerResponse

    private_key, public_key = rsa_keys
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    _install_fake_jwks(monkeypatch, public_pem)

    now = datetime.now(UTC)
    mock_service = AsyncMock()
    mock_service.create.return_value = ConsumerResponse(
        id=1,
        client_id=42,
        consumer_phone_number="9000000000",
        consumer_email_id="consumer@example.com",
        is_approved=True,
        status="READY",
        created_at=now,
        updated_at=now,
    )

    app = create_app()
    app.dependency_overrides[get_consumer_service] = lambda: mock_service
    app.dependency_overrides[get_client_repository] = lambda: mock_client_repository
    token = _encode_token(
        private_key,
        email="user@example.com",
        **{"cognito:groups": ["approved-clients"]},
    )
    client = TestClient(app)
    response = client.post(
        "/v1/consumers?client_email_id=user@example.com",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "consumer_phone_number": "9000000000",
            "consumer_email_id": "consumer@example.com",
        },
    )
    assert response.status_code == 201


def test_m2m_access_token_with_sub_client_id_is_accepted(
    monkeypatch: pytest.MonkeyPatch, rsa_keys, mock_client_repository
) -> None:
    from cryptography.hazmat.primitives import serialization
    from fastapi.testclient import TestClient
    from unittest.mock import MagicMock

    from app.core.dependencies import get_client_repository, get_search_service
    from app.main import create_app

    private_key, public_key = rsa_keys
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    _install_fake_jwks(monkeypatch, public_pem)

    mock_service = MagicMock()
    mock_service.search.return_value = ([], "user@example.com")

    app = create_app()
    app.dependency_overrides[get_search_service] = lambda: mock_service
    app.dependency_overrides[get_client_repository] = lambda: mock_client_repository
    token = _encode_token(
        private_key,
        sub="m2m-client-id",
        client_id=None,
        aud=None,
    )
    client = TestClient(app)
    response = client.post(
        "/v1/search",
        json={"phone_number": "911171366880", "query": "hello"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_clients_me_uses_session_email_when_token_has_no_email(
    monkeypatch: pytest.MonkeyPatch, rsa_keys, mock_client_repository
) -> None:
    from datetime import UTC, datetime
    from cryptography.hazmat.primitives import serialization
    from fastapi.testclient import TestClient
    from unittest.mock import AsyncMock

    from app.core.dependencies import get_client_service
    from app.main import create_app
    from app.schemas.clients import ClientProfileResponse

    private_key, public_key = rsa_keys
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    _install_fake_jwks(monkeypatch, public_pem)

    now = datetime.now(UTC)
    mock_service = AsyncMock()
    mock_service.get_profile_for_principal.return_value = None
    mock_service.ensure_on_sign_in.return_value = ClientProfileResponse(
        id=1,
        client_phone_number=None,
        client_business_phone_number="911171366880",
        client_name="Approved User",
        client_email_id="user@example.com",
        created_at=now,
    )

    app = create_app()
    app.dependency_overrides[get_client_service] = lambda: mock_service
    token = _encode_token(
        private_key,
        **{"cognito:groups": ["approved-clients"]},
    )
    client = TestClient(app)
    response = client.get(
        "/v1/clients/me",
        headers={
            "Authorization": f"Bearer {token}",
            "X-RelayDesk-User-Email": "user@example.com",
        },
    )
    assert response.status_code == 200
    assert response.json()["client_email_id"] == "user@example.com"
    mock_service.ensure_on_sign_in.assert_awaited_once_with(
        client_email_id="user@example.com",
        cognito_sub="user-123",
    )


def test_clients_me_returns_profile_by_cognito_sub(
    monkeypatch: pytest.MonkeyPatch, rsa_keys
) -> None:
    from datetime import UTC, datetime
    from cryptography.hazmat.primitives import serialization
    from fastapi.testclient import TestClient
    from unittest.mock import AsyncMock

    from app.core.dependencies import get_client_service
    from app.main import create_app
    from app.schemas.clients import ClientProfileResponse

    private_key, public_key = rsa_keys
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    _install_fake_jwks(monkeypatch, public_pem)

    now = datetime.now(UTC)
    mock_service = AsyncMock()
    mock_service.get_profile_for_principal.return_value = ClientProfileResponse(
        id=2,
        client_phone_number=None,
        client_business_phone_number="911171366880",
        client_name="Linked User",
        client_email_id="linked@example.com",
        created_at=now,
    )

    app = create_app()
    app.dependency_overrides[get_client_service] = lambda: mock_service
    token = _encode_token(
        private_key,
        **{"cognito:groups": ["approved-clients"]},
    )
    client = TestClient(app)
    response = client.get(
        "/v1/clients/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["client_email_id"] == "linked@example.com"
    mock_service.ensure_on_sign_in.assert_not_awaited()
