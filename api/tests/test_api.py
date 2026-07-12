import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app.core.dependencies import get_client_repository
from app.main import create_app


@pytest.fixture
def mock_client_repository() -> AsyncMock:
    from datetime import UTC, datetime

    from app.domain.client_models import Client

    repository = AsyncMock()
    repository.get_by_email.return_value = Client(
        id=1,
        client_phone_number=None,
        client_business_phone_number="911171366880",
        client_name="Test Client",
        client_email_id="user@example.com",
        created_at=datetime.now(UTC),
    )
    repository.get_by_business_phone.return_value = repository.get_by_email.return_value
    return repository


def test_health() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_qdrant_repository_search_maps_payload() -> None:
    from app.core.config import Settings
    from app.db.qdrant_repository import QdrantRepository

    client = MagicMock()
    search_result = MagicMock()
    search_result.score = 0.88
    search_result.payload = {"text": "Senior Java engineer", "source_uri": "resume.pdf"}
    query_response = MagicMock()
    query_response.points = [search_result]
    client.query_points.return_value = query_response

    settings = Settings()
    repo = QdrantRepository(settings, client=client)
    hits = repo.search(
        "phone_911171366880",
        query_vector=[0.1, 0.2],
        limit=3,
    )
    assert hits[0].text == "Senior Java engineer"
    assert hits[0].source_uri == "resume.pdf"


def test_chunk_text_splits_with_overlap() -> None:
    from app.services.document_service import DocumentService

    text = "word " * 300
    chunks = DocumentService._chunk_text(text, max_chars=100, overlap=20)
    assert len(chunks) > 1
    assert all(len(chunk) <= 100 for chunk in chunks)


def test_search_requires_collection_or_phone(mock_client_repository: AsyncMock) -> None:
    app = create_app()
    app.dependency_overrides[get_client_repository] = lambda: mock_client_repository
    client = TestClient(app)
    response = client.post("/v1/search", json={"query": "hello"})
    assert response.status_code == 400


def test_collection_from_email() -> None:
    from app.core.collections import (
        collection_from_email,
        collection_from_phone,
        resolve_collection,
    )

    assert collection_from_email("Client@Example.com") == "client@example.com"
    assert collection_from_phone("+911171366880") == "phone_911171366880"
    assert resolve_collection(client_email_id="client@example.com") == "client@example.com"
    assert resolve_collection(collection="custom") == "custom"


def test_collection_from_phone_legacy() -> None:
    from app.core.collections import collection_from_phone, resolve_collection

    assert collection_from_phone("+911171366880") == "phone_911171366880"
    assert resolve_collection(phone_number="911171366880") == "phone_911171366880"


def test_search_service_passes_score_threshold_to_qdrant() -> None:
    from app.core.config import Settings
    from app.domain.models import RagSearchHit
    from app.services.search_service import SearchService

    settings = Settings(rag_min_score=0.3)
    qdrant = MagicMock()
    qdrant.search.return_value = [
        RagSearchHit(text="relevant", score=0.55, source_uri="a.txt"),
    ]
    embedding_service = MagicMock()
    embedding_service.create_embeddings.return_value = MagicMock(
        embeddings=[[0.1, 0.2]],
        cache_hits=0,
        cache_misses=1,
    )

    service = SearchService(settings, qdrant, embedding_service)
    hits, collection = service.search(
        query="workforce",
        max_results=5,
        client_email_id="client@example.com",
    )

    assert collection == "client@example.com"
    assert len(hits) == 1
    assert hits[0].text == "relevant"
    _, kwargs = qdrant.search.call_args
    assert kwargs["score_threshold"] == pytest.approx(0.3)


def test_search_invalid_phone(mock_client_repository: AsyncMock) -> None:
    mock_client_repository.get_by_business_phone.return_value = None
    app = create_app()
    app.dependency_overrides[get_client_repository] = lambda: mock_client_repository
    client = TestClient(app)
    response = client.post(
        "/v1/search",
        json={"phone_number": "abc", "query": "hello"},
    )
    assert response.status_code == 400


def test_create_embeddings() -> None:
    from app.core.dependencies import get_embedding_service
    from app.domain.models import EmbeddingBatchResult
    from app.main import create_app

    mock_service = MagicMock()
    mock_service.create_embeddings.return_value = EmbeddingBatchResult(
        model="text-embedding-3-small",
        dimensions=3,
        embeddings=[[0.1, 0.2, 0.3]],
        cache_hits=1,
        cache_misses=0,
    )

    app = create_app()
    app.dependency_overrides[get_embedding_service] = lambda: mock_service
    test_client = TestClient(app)

    response = test_client.post("/v1/embeddings", json={"texts": ["hello"]})
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "text-embedding-3-small"
    assert data["embeddings"] == [[0.1, 0.2, 0.3]]
