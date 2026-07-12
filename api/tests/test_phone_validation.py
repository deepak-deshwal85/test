from __future__ import annotations

import pytest

from app.domain.phone_validation import (
    combine_phone_parts,
    normalize_optional_phone_number,
    normalize_phone_number,
)


def test_normalize_phone_number_strips_plus_and_spaces() -> None:
    assert normalize_phone_number("+91 91117 1366880") == "91911171366880"
    assert normalize_phone_number("9876543210") == "9876543210"


def test_normalize_phone_number_rejects_too_short() -> None:
    with pytest.raises(ValueError, match="8–15"):
        normalize_phone_number("1234567")


def test_combine_phone_parts() -> None:
    assert combine_phone_parts("91", "9876543210") == "919876543210"
    assert combine_phone_parts("+91", "9876543210") == "919876543210"


def test_combine_phone_parts_validates_country_code() -> None:
    with pytest.raises(ValueError, match="Country code"):
        combine_phone_parts("", "9876543210")


def test_combine_phone_parts_validates_national_number() -> None:
    with pytest.raises(ValueError, match="6–12"):
        combine_phone_parts("91", "12345")


def test_normalize_optional_phone_number() -> None:
    assert normalize_optional_phone_number(None) is None
    assert normalize_optional_phone_number("") is None
    assert normalize_optional_phone_number("  ") is None
    assert normalize_optional_phone_number("919876543210") == "919876543210"
