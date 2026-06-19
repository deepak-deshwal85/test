import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from paths import CONFIG_DIR

logger = logging.getLogger("agent-telephone-agent")

CONFIG_FILE_PATTERN = "phone_number_{phone_number}.json"


@dataclass(frozen=True)
class ClientConfig:
    phone_number: str
    client_name: str
    xai_collection_id: str


def normalize_phone_number(phone: str) -> str:
    return re.sub(r"\D", "", phone)


def config_path_for_phone(phone_number: str) -> Path:
    return CONFIG_DIR / CONFIG_FILE_PATTERN.format(phone_number=phone_number)


def load_client_config(phone_number: str) -> ClientConfig:
    path = config_path_for_phone(phone_number)
    if not path.is_file():
        raise FileNotFoundError(
            f"No client config found for phone number {phone_number!r}"
        )

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    return ClientConfig(
        phone_number=data["phone_number"],
        client_name=data["client_name"],
        xai_collection_id=data["xai_collection_id"],
    )


def resolve_client_config(phone_digits: str) -> ClientConfig | None:
    """Match a SIP phone number to a per-number client config."""
    if not phone_digits:
        return None

    if config_path_for_phone(phone_digits).is_file():
        return load_client_config(phone_digits)

    for config_file in sorted(CONFIG_DIR.glob("phone_number_*.json")):
        suffix = config_file.stem.removeprefix("phone_number_")
        if phone_digits == suffix or phone_digits.endswith(suffix):
            return load_client_config(suffix)

    logger.warning("No client config matched phone digits %s", phone_digits)
    return None
