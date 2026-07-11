import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from client_config import load_client_config, resolve_client_config


def test_load_client_config_for_phone_911171366880():
    config = load_client_config("911171366880")
    assert config.phone_number == "911171366880"
    assert config.client_name == "Deepak Kumar"
    assert config.calcom is not None
    assert config.calcom.username == "deepak-kumar-a7vq7q"
    assert config.calcom.event_type_slug == "30min"


def test_load_client_config_for_phone_6789():
    config = load_client_config("6789")
    assert config.client_name == "Bob Smith"


def test_resolve_client_config_matches_full_number():
    config = resolve_client_config("911171366880")
    assert config is not None
    assert config.phone_number == "911171366880"


def test_resolve_client_config_returns_none_for_unknown_number():
    assert resolve_client_config("0000") is None
