import pytest

from app.core.config import get_settings


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


def test_valid_access_token_is_accepted(monkeypatch: pytest.MonkeyPatch, rsa_keys) -> None:
    from cryptography.hazmat.primitives import serialization
    from fastapi.testclient import TestClient

    from app.core import oauth as oauth_module
    from app.core.dependencies import get_search_service
    from app.main import create_app
    from unittest.mock import MagicMock

    private_key, public_key = rsa_keys
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    class FakeSigningKey:
        key = public_pem

    class FakeJwkClient:
        def get_signing_key_from_jwt(self, _token):
            return FakeSigningKey()

    monkeypatch.setattr(oauth_module, "_jwks_client", lambda _url: FakeJwkClient())

    mock_service = MagicMock()
    mock_service.search.return_value = ([], "phone_911171366880")

    app = create_app()
    app.dependency_overrides[get_search_service] = lambda: mock_service
    token = _encode_token(private_key)
    client = TestClient(app)
    response = client.post(
        "/v1/search",
        json={"phone_number": "911171366880", "query": "hello"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_m2m_access_token_with_sub_client_id_is_accepted(
    monkeypatch: pytest.MonkeyPatch, rsa_keys
) -> None:
    from cryptography.hazmat.primitives import serialization
    from fastapi.testclient import TestClient
    from unittest.mock import MagicMock

    from app.core import oauth as oauth_module
    from app.core.dependencies import get_search_service
    from app.main import create_app

    private_key, public_key = rsa_keys
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    class FakeSigningKey:
        key = public_pem

    class FakeJwkClient:
        def get_signing_key_from_jwt(self, _token):
            return FakeSigningKey()

    monkeypatch.setattr(oauth_module, "_jwks_client", lambda _url: FakeJwkClient())

    mock_service = MagicMock()
    mock_service.search.return_value = ([], "phone_911171366880")

    app = create_app()
    app.dependency_overrides[get_search_service] = lambda: mock_service
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
