import logging
import os
from dataclasses import dataclass
from pathlib import Path

from client_config import ClientConfig
from paths import CONFIG_DIR, DATA_DIR, PROJECT_ROOT

logger = logging.getLogger("agent-telephone-agent")

RAG_PROPERTIES_PATH = CONFIG_DIR / "rag.properties"
SUPPORTED_RAG_BACKENDS = frozenset({"xai", "qdrant"})
SUPPORTED_QDRANT_ACCESS = frozenset({"api", "direct"})


@dataclass(frozen=True)
class RagSettings:
    backend: str
    max_results: int
    embedder_provider: str
    embedder_model: str
    embedder_dimensions: int
    qdrant_url: str
    rag_api_base_url: str
    qdrant_access: str
    embedder_cache_enabled: bool
    embedder_cache_path: Path


def _parse_properties_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    return key.strip(), value.strip()


def load_properties_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}

    properties: dict[str, str] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            parsed = _parse_properties_line(line)
            if parsed is None:
                continue
            properties[parsed[0]] = parsed[1]
    return properties


def load_rag_settings(properties_path: Path = RAG_PROPERTIES_PATH) -> RagSettings:
    properties = load_properties_file(properties_path)
    backend = (
        os.getenv("RAG_BACKEND", properties.get("rag.backend", "xai")).strip().lower()
    )
    if backend not in SUPPORTED_RAG_BACKENDS:
        raise ValueError(
            f"Unsupported rag.backend {backend!r}. Use one of: {sorted(SUPPORTED_RAG_BACKENDS)}"
        )

    max_results = int(
        os.getenv("RAG_MAX_RESULTS", properties.get("rag.max_results", "5"))
    )
    embedder_provider = os.getenv(
        "RAG_EMBEDDER_PROVIDER",
        properties.get("rag.embedder.provider", "openai"),
    ).strip()
    embedder_model = os.getenv(
        "RAG_EMBEDDER_MODEL",
        os.getenv("EMBEDDING_MODEL", properties.get("rag.embedder.model", "text-embedding-3-small")),
    ).strip()
    embedder_dimensions = int(
        os.getenv(
            "RAG_EMBEDDER_DIMENSIONS",
            properties.get("rag.embedder.dimensions", "1536"),
        )
    )
    qdrant_url = os.getenv(
        "QDRANT_URL",
        properties.get("qdrant.url", "http://127.0.0.1:6333"),
    ).strip()
    rag_api_base_url = os.getenv(
        "RAG_API_BASE_URL",
        properties.get("rag.api.base_url", "http://127.0.0.1:8090"),
    ).strip()
    qdrant_access = os.getenv(
        "RAG_QDRANT_ACCESS",
        properties.get("rag.qdrant.access", "api"),
    ).strip().lower()
    if qdrant_access not in SUPPORTED_QDRANT_ACCESS:
        raise ValueError(
            f"Unsupported rag.qdrant.access {qdrant_access!r}. "
            f"Use one of: {sorted(SUPPORTED_QDRANT_ACCESS)}"
        )

    embedder_cache_enabled = os.getenv(
        "RAG_EMBEDDER_CACHE",
        properties.get("rag.embedder.cache.enabled", "true"),
    ).strip().lower() in {"1", "true", "yes", "on"}
    cache_path_raw = os.getenv(
        "RAG_EMBEDDER_CACHE_PATH",
        properties.get(
            "rag.embedder.cache.path",
            str(DATA_DIR / "embedding_cache.sqlite"),
        ),
    )
    embedder_cache_path = Path(cache_path_raw).expanduser()
    if not embedder_cache_path.is_absolute():
        embedder_cache_path = PROJECT_ROOT / embedder_cache_path

    return RagSettings(
        backend=backend,
        max_results=max_results,
        embedder_provider=embedder_provider,
        embedder_model=embedder_model,
        embedder_dimensions=embedder_dimensions,
        qdrant_url=qdrant_url,
        rag_api_base_url=rag_api_base_url,
        qdrant_access=qdrant_access,
        embedder_cache_enabled=embedder_cache_enabled,
        embedder_cache_path=embedder_cache_path,
    )


def resolve_rag_backend(
    client_config: ClientConfig,
    settings: RagSettings | None = None,
) -> str:
    rag_settings = settings or load_rag_settings()
    if client_config.rag_backend:
        backend = client_config.rag_backend.strip().lower()
    else:
        backend = rag_settings.backend

    if backend not in SUPPORTED_RAG_BACKENDS:
        raise ValueError(
            f"Unsupported rag backend {backend!r} for phone {client_config.phone_number}"
        )
    return backend


def resolve_qdrant_collection(
    client_config: ClientConfig,
    settings: RagSettings | None = None,
) -> str:
    _ = settings
    if client_config.qdrant_collection:
        return client_config.qdrant_collection.strip()
    return f"phone_{client_config.phone_number}"


def resolve_rag_api_url(
    client_config: ClientConfig,
    settings: RagSettings | None = None,
) -> str:
    rag_settings = settings or load_rag_settings()
    if client_config.rag_api_url:
        return client_config.rag_api_url.strip().rstrip("/")
    return rag_settings.rag_api_base_url.rstrip("/")
