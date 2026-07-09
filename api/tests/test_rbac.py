import pytest

from app.core.rbac import Permission, RelayDeskRole, resolve_role, role_has_permission


def test_resolve_role_prefers_admin_over_guest() -> None:
    role = resolve_role(frozenset({"guest-clients", "relaydesk-admins"}))
    assert role == RelayDeskRole.ADMIN


def test_resolve_role_defaults_to_guest() -> None:
    assert resolve_role(frozenset(), default_guest=True) == RelayDeskRole.GUEST


def test_resolve_role_without_default_stays_none() -> None:
    assert resolve_role(frozenset()) is None


def test_guest_permissions() -> None:
    assert role_has_permission(RelayDeskRole.GUEST, Permission.READ)
    assert not role_has_permission(RelayDeskRole.GUEST, Permission.DOCUMENT_WRITE)
    assert not role_has_permission(RelayDeskRole.GUEST, Permission.ADMIN)


def test_approved_client_permissions() -> None:
    assert role_has_permission(RelayDeskRole.APPROVED, Permission.READ)
    assert role_has_permission(RelayDeskRole.APPROVED, Permission.DOCUMENT_WRITE)
    assert not role_has_permission(RelayDeskRole.APPROVED, Permission.ADMIN)


def test_admin_permissions() -> None:
    assert role_has_permission(RelayDeskRole.ADMIN, Permission.ADMIN)
