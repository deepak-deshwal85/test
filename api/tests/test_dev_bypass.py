"""Tests for OAUTH_DISABLED local bypass with UI session headers."""

from __future__ import annotations

from app.core.oauth import dev_bypass_principal
from app.core.rbac import RelayDeskRole


def test_dev_bypass_without_headers_uses_dev_admin() -> None:
    principal = dev_bypass_principal()
    assert principal.email == "dev@example.com"
    assert principal.role == RelayDeskRole.ADMIN


def test_dev_bypass_honors_session_email_and_role() -> None:
    principal = dev_bypass_principal(
        session_email="deepakdeshwal85@yahoo.com",
        session_role="approved-clients",
    )
    assert principal.email == "deepakdeshwal85@yahoo.com"
    assert principal.role == RelayDeskRole.APPROVED


def test_dev_bypass_approved_client_is_not_admin() -> None:
    from app.core.rbac import Permission

    principal = dev_bypass_principal(
        session_email="client@example.com",
        session_role="approved-clients",
    )
    assert not principal.has_permission(Permission.ADMIN)
