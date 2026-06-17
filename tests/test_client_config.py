import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from client_config import load_client_config, resolve_client_config
from rag import RagChunk, RagStore


def test_load_client_config_for_phone_911171366880():
    config = load_client_config("911171366880")
    assert config.phone_number == "911171366880"
    assert config.client_name == "Deepak Kumar"
    assert config.knowledge_base_doc == "resume_1.pdf"
    assert config.embeddings_file == "phone_number_911171366880.json"


def test_load_client_config_for_phone_6789():
    config = load_client_config("6789")
    assert config.client_name == "Bob Smith"
    assert config.knowledge_base_doc == "resume_2.pdf"


def test_resolve_client_config_matches_full_number():
    config = resolve_client_config("911171366880")
    assert config is not None
    assert config.phone_number == "911171366880"


def test_resolve_client_config_returns_none_for_unknown_number():
    assert resolve_client_config("0000") is None


def _mock_embed_query(text: str) -> list[float]:
    if "python" in text.lower():
        return [1.0, 0.0]
    return [0.0, 1.0]


def test_rag_store_retrieves_most_relevant_chunk():
    store = RagStore(
        model_name="test-model",
        chunks=[
            RagChunk(text="Alice knows Python and FastAPI.", embedding=[1.0, 0.0]),
            RagChunk(text="Bob focuses on machine learning.", embedding=[0.0, 1.0]),
        ],
        embed_query=_mock_embed_query,
    )

    matches = store.retrieve("What Python experience is listed?")
    assert matches[0][1].startswith("Alice")


def test_rag_store_answer_without_matches():
    store = RagStore(model_name="test-model", chunks=[], embed_query=_mock_embed_query)
    assert "no matching information" in store.answer("anything").lower()
