from __future__ import annotations

MIN_FULL_PHONE_DIGITS = 8
MAX_FULL_PHONE_DIGITS = 15
MIN_COUNTRY_CODE_DIGITS = 1
MAX_COUNTRY_CODE_DIGITS = 3
MIN_NATIONAL_DIGITS = 6
MAX_NATIONAL_DIGITS = 12


def digits_only(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def normalize_phone_number(value: str) -> str:
    """Strip non-digits and validate E.164 length (without +)."""
    digits = digits_only(value)
    if not digits:
        raise ValueError("Phone number is required")
    if len(digits) < MIN_FULL_PHONE_DIGITS or len(digits) > MAX_FULL_PHONE_DIGITS:
        raise ValueError(
            f"Phone number must be {MIN_FULL_PHONE_DIGITS}–{MAX_FULL_PHONE_DIGITS} "
            "digits including country code"
        )
    return digits


def combine_phone_parts(country_code: str, national_number: str) -> str:
    """Combine country code + local number; store digits only (no +)."""
    cc = digits_only(country_code)
    nn = digits_only(national_number)
    if not cc:
        raise ValueError("Country code is required")
    if len(cc) < MIN_COUNTRY_CODE_DIGITS or len(cc) > MAX_COUNTRY_CODE_DIGITS:
        raise ValueError(
            f"Country code must be {MIN_COUNTRY_CODE_DIGITS}–{MAX_COUNTRY_CODE_DIGITS} digits"
        )
    if not nn:
        raise ValueError("Phone number is required")
    if len(nn) < MIN_NATIONAL_DIGITS or len(nn) > MAX_NATIONAL_DIGITS:
        raise ValueError(
            f"Phone number must be {MIN_NATIONAL_DIGITS}–{MAX_NATIONAL_DIGITS} digits "
            "without country code"
        )
    return normalize_phone_number(f"{cc}{nn}")


def normalize_optional_phone_number(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return normalize_phone_number(stripped)
