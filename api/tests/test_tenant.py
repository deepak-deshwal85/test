import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app.core.oauth import AuthenticatedPrincipal
from app.core.rbac import RelayDeskRole
from app.core.tenant import (
    ensure_client_email_scope,
    ensure_collection_access,
    filter_collections,
    is_scope_unrestricted,
    resolve_client_scope,
)
from app.domain.client_models import Client


def _principal(
    *,
    email: str | None = "client@example.com",
    role: RelayDeskRole | None = RelayDeskRole.GUEST,
    is_m2m: bool = False,
) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        subject="sub-1",
        client_id="ui-client",
        username=None,
        email=email,
        scopes=frozenset({"relaydesk-api/access"}),
        token_use="access",
        groups=frozenset({role.value}) if role else frozenset(),
        role=role,
        is_m2m=is_m2m,
    )


def _client() -> Client:
    return Client(
        id=1,
        client_phone_number=None,
        client_business_phone_number="91911171366880",
        client_name="Acme",
        client_email_id="client@example.com",
        cognito_sub="sub-1",
        created_at=datetime.now(UTC),
    )


def test_m2m_is_unrestricted() -> None:
    principal = _principal(is_m2m=True, role=None, email=None)
    assert is_scope_unrestricted(principal) is True


def test_admin_is_unrestricted() -> None:
    principal = _principal(role=RelayDeskRole.ADMIN)
    assert is_scope_unrestricted(principal) is True


def test_guest_email_scope_mismatch() -> None:
    principal = _principal(email="other@example.com")
    with pytest.raises(HTTPException) as exc:
        ensure_client_email_scope(principal, "client@example.com")
    assert exc.value.status_code == 403


def test_guest_email_scope_match() -> None:
    principal = _principal(email="client@example.com")
    assert (
        ensure_client_email_scope(principal, "client@example.com")
        == "client@example.com"
    )


def test_resolve_scope_without_profile_returns_empty_collection_scope() -> None:
    principal = _principal()
    scope = resolve_client_scope(
        principal,
        client_email_id="client@example.com",
        client=None,
    )
    assert scope.unrestricted is False
    assert scope.client_email_id == "client@example.com"
    assert scope.client_business_phone_number is None
    assert scope.collection_name is None
    assert filter_collections(scope, ["phone_91911171366880"]) == []


def test_resolve_scope_for_ui_client_with_profile() -> None:
    principal = _principal()
    scope = resolve_client_scope(
        principal,
        client_email_id="client@example.com",
        client=_client(),
    )
    assert scope.unrestricted is False
    assert scope.client_business_phone_number == "91911171366880"
    assert scope.collection_name == "phone_91911171366880"


def test_filter_collections_for_scoped_client() -> None:
    scope = resolve_client_scope(
        _principal(),
        client_email_id="client@example.com",
        client=_client(),
    )
    filtered = filter_collections(
        scope,
        ["phone_91911171366880", "phone_9999999999"],
    )
    assert filtered == ["phone_91911171366880"]


def test_ensure_collection_access_denies_other_collection() -> None:
    scope = resolve_client_scope(
        _principal(),
        client_email_id="client@example.com",
        client=_client(),
    )
    with pytest.raises(HTTPException) as exc:
        ensure_collection_access(scope, "phone_9999999999")
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_client_profile_upsert_requires_ui_user() -> None:
    from datetime import UTC, datetime
    from unittest.mock import AsyncMock

    from fastapi.testclient import TestClient

    from app.core.dependencies import get_client_repository, get_client_service
    from app.main import create_app
    from app.schemas.clients import ClientProfileResponse

    now = datetime.now(UTC)
    mock_service = AsyncMock()
    mock_repository = AsyncMock()
    mock_repository.get_by_cognito_sub.return_value = None
    mock_service.upsert_profile.return_value = ClientProfileResponse(
        id=1,
        client_phone_number="9876543210",
        client_business_phone_number="911171366880",
        client_name="Jane",
        client_email_id="jane@example.com",
        created_at=now,
    )

    app = create_app()
    app.dependency_overrides[get_client_service] = lambda: mock_service
    app.dependency_overrides[get_client_repository] = lambda: mock_repository
    test_client = TestClient(app)

    response = test_client.put(
        "/v1/clients/profile",
        json={
            "client_name": "Jane",
            "client_phone_number": "9876543210",
        },
    )
    assert response.status_code == 200
