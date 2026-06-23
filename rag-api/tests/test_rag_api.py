import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rag.backends.models import RagSearchHit, format_search_hits
from rag.qdrant_store import QdrantVectorStore


def test_format_search_hits_returns_plain_language():
    message = format_search_hits(
        [RagSearchHit(text="Built RAG pipelines.", score=0.8, source_uri="resume.pdf")]
    )
    assert "Relevant document excerpts" in message
    assert "Built RAG pipelines." in message


def test_qdrant_store_search_maps_payload():
    client = MagicMock()
    client.collection_exists.return_value = True
    search_result = MagicMock()
    search_result.score = 0.88
    search_result.payload = {"text": "Senior Java engineer", "source_uri": "resume.pdf"}
    query_response = MagicMock()
    query_response.points = [search_result]
    client.query_points.return_value = query_response

    store = QdrantVectorStore(url="http://qdrant.test", client=client)
    hits = store.search(
        "phone_911171366880",
        query_vector=[0.1, 0.2],
        limit=3,
    )
    assert hits[0].text == "Senior Java engineer"
    assert hits[0].source_uri == "resume.pdf"
