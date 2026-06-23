from __future__ import annotations


def collection_from_phone(phone_number: str) -> str:
    digits = "".join(character for character in phone_number if character.isdigit())
    if not digits:
        raise ValueError(f"Invalid phone_number: {phone_number!r}")
    return f"phone_{digits}"


def resolve_collection(
    *,
    phone_number: str | None = None,
    collection: str | None = None,
) -> str:
    if collection:
        return collection.strip()
    if phone_number:
        return collection_from_phone(phone_number)
    raise ValueError("Provide either phone_number or collection")
