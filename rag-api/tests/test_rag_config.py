import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from client_config import ClientConfig, load_client_config
from rag.config import (
    RAG_PROPERTIES_PATH,
    load_rag_settings,
    resolve_qdrant_collection,
    resolve_rag_backend,
)


def test_load_rag_settings_reads_properties_file():
    settings = load_rag_settings(RAG_PROPERTIES_PATH)
    assert settings.backend == "qdrant"
    assert settings.max_results == 5
    assert settings.qdrant_url.startswith("http")
    assert settings.embedder_cache_enabled is True
    assert settings.embedder_cache_path.name == "embedding_cache.sqlite"


def test_resolve_rag_backend_uses_client_override():
    client = ClientConfig(
        phone_number="911171366880",
        client_name="Deepak Kumar",
        xai_collection_id="collection_test",
        rag_backend="qdrant",
    )
    assert resolve_rag_backend(client) == "qdrant"


def test_resolve_qdrant_collection_defaults_to_phone():
    client = ClientConfig(
        phone_number="911171366880",
        client_name="Deepak Kumar",
        xai_collection_id="collection_test",
    )
    assert resolve_qdrant_collection(client) == "phone_911171366880"


def test_load_client_config_reads_qdrant_fields():
    config = load_client_config("911171366880")
    assert config.qdrant_collection is None
