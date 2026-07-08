from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import HTTPException, status
from jwt import PyJWKClient

from app.core.config import Settings

logger = logging.getLogger("relaydesk-api")


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    subject: str
    client_id: str | None
    username: str | None
    scopes: frozenset[str]
    token_use: str


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
        return AuthenticatedPrincipal(
            subject="dev-user",
            client_id=None,
            username="dev",
            scopes=frozenset({"relaydesk-api/access"}),
            token_use="access",
        )

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
        logger.info("jwt validation failed: %s", exc)
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

    return AuthenticatedPrincipal(
        subject=str(claims["sub"]),
        client_id=client_id_str,
        username=str(claims["username"]) if claims.get("username") else None,
        scopes=scopes,
        token_use=token_use,
    )
