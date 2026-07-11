from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status

from app.core.collections import collection_from_email
from app.core.oauth import AuthenticatedPrincipal
from app.core.rbac import Permission
from app.db.postgres.client_repository import ClientRepository
from app.domain.client_models import Client


def is_scope_unrestricted(principal: AuthenticatedPrincipal) -> bool:
    return principal.is_m2m or principal.has_permission(Permission.ADMIN)


def principal_email(principal: AuthenticatedPrincipal) -> str | None:
    if principal.email:
        return principal.email.lower()
    username = principal.username
    if username and "@" in username:
        return username.lower()
    return None


def resolve_user_email(
    principal: AuthenticatedPrincipal,
    session_email: str | None = None,
) -> str | None:
    """Email from the access token, or from the UI session header when Cognito omits email."""
    token_email = principal_email(principal)
    if token_email:
        return token_email
    if session_email:
        normalized = session_email.strip().lower()
        if "@" in normalized:
            return normalized
    return None


async def verify_client_email_scope(
    principal: AuthenticatedPrincipal,
    client_email_id: str,
    repository: ClientRepository,
) -> str:
    normalized = client_email_id.strip().lower()
    if is_scope_unrestricted(principal):
        return normalized

    token_email = principal_email(principal)
    if token_email and token_email != normalized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client email scope mismatch",
        )

    client_by_email = await repository.get_by_email(normalized)
    client_by_sub = await repository.get_by_cognito_sub(principal.subject)

    if (
        client_by_email is not None
        and client_by_email.cognito_sub
        and client_by_email.cognito_sub != principal.subject
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client email scope mismatch",
        )

    if (
        client_by_sub is not None
        and client_by_sub.client_email_id != normalized
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client email scope mismatch",
        )

    if token_email == normalized:
        return normalized
    if client_by_email is not None and client_by_email.cognito_sub == principal.subject:
        return normalized
    if client_by_sub is not None and client_by_sub.client_email_id == normalized:
        return normalized
    if client_by_email is None and client_by_sub is None:
        return normalized

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Client email scope mismatch",
    )


def ensure_client_email_scope(
    principal: AuthenticatedPrincipal,
    client_email_id: str,
) -> str:
    normalized = client_email_id.strip().lower()
    if is_scope_unrestricted(principal):
        return normalized
    token_email = principal_email(principal)
    if not token_email or token_email != normalized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client email scope mismatch",
        )
    return normalized


@dataclass(frozen=True)
class ResolvedClientScope:
    client_email_id: str | None
    client_business_phone_number: str | None
    collection_name: str | None
    unrestricted: bool


def resolve_client_scope(
    principal: AuthenticatedPrincipal,
    *,
    client_email_id: str | None,
    client: Client | None,
) -> ResolvedClientScope:
    if is_scope_unrestricted(principal):
        if client_email_id and client is not None:
            business_phone = client.client_business_phone_number
            collection = collection_from_email(client.client_email_id)
            return ResolvedClientScope(
                client_email_id=client.client_email_id,
                client_business_phone_number=business_phone,
                collection_name=collection,
                unrestricted=True,
            )
        return ResolvedClientScope(None, None, None, True)

    if not client_email_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_email_id is required",
        )

    normalized = client_email_id.strip().lower()
    if client is None:
        return ResolvedClientScope(
            client_email_id=normalized,
            client_business_phone_number=None,
            collection_name=collection_from_email(normalized),
            unrestricted=False,
        )

    business_phone = client.client_business_phone_number
    collection = collection_from_email(client.client_email_id)
    return ResolvedClientScope(
        client_email_id=normalized,
        client_business_phone_number=business_phone,
        collection_name=collection,
        unrestricted=False,
    )


def ensure_collection_access(scope: ResolvedClientScope, collection: str) -> None:
    if scope.unrestricted:
        return
    if scope.collection_name != collection.strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Collection not allowed for this client",
        )


def filter_collections(scope: ResolvedClientScope, collections: list[str]) -> list[str]:
    if scope.unrestricted:
        return collections
    if scope.collection_name is None:
        return []
    return [name for name in collections if name == scope.collection_name]
