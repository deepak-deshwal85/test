from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from rag_client.config import RagClientSettings, resolve_rag_api_url
from rag_client.oauth_token import get_cognito_token_provider

logger = logging.getLogger("relaydesk-agent")


@dataclass(frozen=True)
class ResolvedClientEmail:
    client_email_id: str
    collection_name: str


async def resolve_client_email_by_phone(
    *,
    phone_digits: str,
    base_url: str,
    http_client: httpx.AsyncClient | None = None,
) -> ResolvedClientEmail | None:
    """Look up client_email_id from business phone via the RAG API (M2M)."""
    if not phone_digits:
        return None

    owns_client = http_client is None
    client = http_client or httpx.AsyncClient(
        base_url=base_url.rstrip("/"),
        timeout=httpx.Timeout(15.0, connect=5.0),
    )
    headers: dict[str, str] = {}
    token_provider = get_cognito_token_provider()
    if token_provider is not None:
        token = await token_provider.get_access_token()
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = await client.get(
            "/v1/clients/resolve-by-phone",
            params={"phone_number": phone_digits},
            headers=headers,
        )
        if response.status_code == 404:
            logger.warning("no client email found for phone %s", phone_digits)
            return None
        response.raise_for_status()
        data = response.json()
        email = str(data["client_email_id"]).strip().lower()
        collection = str(data.get("collection_name") or email).strip().lower()
        return ResolvedClientEmail(client_email_id=email, collection_name=collection)
    except Exception:
        logger.exception("failed to resolve client email for phone %s", phone_digits)
        return None
    finally:
        if owns_client:
            await client.aclose()


async def resolve_client_email(
    *,
    metadata_email: str | None,
    config_email: str | None,
    phone_digits: str | None,
    settings: RagClientSettings | None = None,
) -> str | None:
    """Resolve tenant email: job metadata → local config → API phone lookup."""
    if metadata_email and "@" in metadata_email:
        return metadata_email.strip().lower()

    if config_email and "@" in config_email:
        return config_email.strip().lower()

    if not phone_digits:
        return None

    from rag_client.config import load_rag_settings

    rag_settings = settings or load_rag_settings()
    base_url = rag_settings.rag_api_base_url
    resolved = await resolve_client_email_by_phone(
        phone_digits=phone_digits,
        base_url=base_url,
    )
    return resolved.client_email_id if resolved else None
