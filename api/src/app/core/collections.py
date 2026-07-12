from __future__ import annotations

from app.domain.consumer_models import normalize_email


def collection_from_email(client_email_id: str) -> str:
    """Qdrant collection name is the normalized client email (no prefix)."""
    return normalize_email(client_email_id)


def collection_from_phone(phone_number: str) -> str:
    """Legacy phone-based collection naming (deprecated)."""
    digits = "".join(character for character in phone_number if character.isdigit())
    if not digits:
        raise ValueError(f"Invalid phone_number: {phone_number!r}")
    return f"phone_{digits}"


def resolve_collection(
    *,
    client_email_id: str | None = None,
    phone_number: str | None = None,
    collection: str | None = None,
) -> str:
    if collection:
        return collection.strip()
    if client_email_id:
        return collection_from_email(client_email_id)
    if phone_number:
        return collection_from_phone(phone_number)
    raise ValueError("Provide client_email_id, phone_number, or collection")
