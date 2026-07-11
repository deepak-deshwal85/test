from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import HTTPException, status
from jwt import PyJWKClient

from app.core.config import Settings
from app.core.rbac import Permission, RelayDeskRole, resolve_role, role_has_permission

logger = logging.getLogger("relaydesk-api")


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    subject: str
    client_id: str | None
    username: str | None
    email: str | None
    scopes: frozenset[str]
    token_use: str
    groups: frozenset[str]
    role: RelayDeskRole | None
    is_m2m: bool

    def has_permission(self, permission: Permission) -> bool:
        if self.is_m2m:
            return True
        if self.role is None:
            return False
        return role_has_permission(self.role, permission)


@lru_cache
def _jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url, cache_keys=True)


def _allowed_client_ids(settings: Settings) -> frozenset[str]:
    return frozenset(
        client_id
        for client_id in (
            settings.cognito_ui_client_id,
            settings.cognito_m2m_client_id,
        )
        if client_id
    )


def _cognito_groups(claims: dict[str, object]) -> frozenset[str]:
    raw = claims.get("cognito:groups")
    if raw is None:
        return frozenset()
    if isinstance(raw, list):
        return frozenset(str(group) for group in raw)
    if isinstance(raw, str):
        return frozenset(part for part in raw.split() if part)
    return frozenset()


def _is_m2m_client(client_id: str | None, settings: Settings) -> bool:
    return bool(
        settings.cognito_m2m_client_id
        and client_id
        and client_id == settings.cognito_m2m_client_id
    )


def _resolve_client_id(claims: dict[str, object]) -> str | None:
    for claim_name in ("client_id", "aud", "azp"):
        claim_value = claims.get(claim_name)
        if claim_value:
            return str(claim_value)

    # Some Cognito client-credentials tokens only carry the app client in `sub`.
    sub = claims.get("sub")
    token_use = claims.get("token_use")
    if token_use == "access" and isinstance(sub, str) and sub:
        return sub
    return None


def validate_access_token(token: str, settings: Settings) -> AuthenticatedPrincipal:
    if settings.oauth_disabled:
        return dev_bypass_principal()

    if not settings.cognito_issuer or not settings.cognito_jwks_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OAuth is not configured",
        )

    try:
        signing_key = _jwks_client(settings.cognito_jwks_url).get_signing_key_from_jwt(
            token
        )
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.cognito_issuer,
            options={
                "verify_aud": False,
                "require": ["exp", "iss", "sub", "token_use"],
            },
        )
    except jwt.PyJWTError as exc:
        logger.warning("jwt validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        ) from exc

    token_use = str(claims.get("token_use", ""))
    if token_use != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is not an access token",
        )

    client_id_str = _resolve_client_id(claims)

    allowed_clients = _allowed_client_ids(settings)
    if allowed_clients and client_id_str not in allowed_clients:
        logger.warning(
            "untrusted oauth client client_id=%r allowed=%s",
            client_id_str,
            sorted(allowed_clients),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Untrusted OAuth client",
        )

    scope_value = claims.get("scope", "")
    scopes = frozenset(str(scope_value).split()) if scope_value else frozenset()

    required_scope = settings.cognito_required_scope
    if required_scope and required_scope not in scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing required scope",
        )

    groups = _cognito_groups(claims)
    is_m2m = _is_m2m_client(client_id_str, settings)
    role = resolve_role(groups, default_guest=not is_m2m)

    username = str(claims["username"]) if claims.get("username") else None
    email = str(claims["email"]).lower() if claims.get("email") else None
    if not email and username and "@" in username:
        email = username.lower()

    return AuthenticatedPrincipal(
        subject=str(claims["sub"]),
        client_id=client_id_str,
        username=username,
        email=email,
        scopes=scopes,
        token_use=token_use,
        groups=groups,
        role=role,
        is_m2m=is_m2m,
    )


def dev_bypass_principal(
    *,
    session_email: str | None = None,
    session_role: str | None = None,
) -> AuthenticatedPrincipal:
    """Local API bypass (OAUTH_DISABLED=true).

    When the UI sends Cognito session headers, honor the signed-in user instead of
    always impersonating dev@example.com. Scripts without headers keep dev admin.
    """
    normalized_email = (
        session_email.strip().lower()
        if session_email and "@" in session_email
        else None
    )

    groups: frozenset[str] = frozenset()
    if session_role and session_role.strip():
        groups = frozenset({session_role.strip()})

    if not normalized_email and not groups:
        return AuthenticatedPrincipal(
            subject="dev-user",
            client_id=None,
            username="dev",
            email="dev@example.com",
            scopes=frozenset({"relaydesk-api/access"}),
            token_use="access",
            groups=frozenset(),
            role=RelayDeskRole.ADMIN,
            is_m2m=False,
        )

    role = resolve_role(groups, default_guest=bool(normalized_email))

    return AuthenticatedPrincipal(
        subject=normalized_email or "oauth-disabled-user",
        client_id=None,
        username=normalized_email,
        email=normalized_email,
        scopes=frozenset({"relaydesk-api/access"}),
        token_use="access",
        groups=groups,
        role=role,
        is_m2m=False,
    )
