from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status

from app.core.collections import collection_from_phone
from app.core.oauth import AuthenticatedPrincipal
from app.core.rbac import Permission
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
    client_phone_number: str | None
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
            collection = collection_from_phone(client.client_phone_number)
            return ResolvedClientScope(
                client_email_id=client.client_email_id,
                client_phone_number=client.client_phone_number,
                collection_name=collection,
                unrestricted=True,
            )
        return ResolvedClientScope(None, None, None, True)

    if not client_email_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="client_email_id is required",
        )

    normalized = ensure_client_email_scope(principal, client_email_id)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client profile not found. Complete authorization profile setup.",
        )

    collection = collection_from_phone(client.client_phone_number)
    return ResolvedClientScope(
        client_email_id=normalized,
        client_phone_number=client.client_phone_number,
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
