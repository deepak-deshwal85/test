import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from client_config import ClientConfig
from rag_client.models import RagSearchHit, filter_relevant_hits
from rag_client.prefetch import (
    DocumentPrefetchCache,
    build_prefetched_context_message,
    extract_message_text,
    requires_sync_turn_completion,
    should_auto_search_user_text,
)


def test_extract_message_text_from_string_list():
    assert extract_message_text(["What is Reliance revenue?"]) == (
        "What is Reliance revenue?"
    )


def test_should_auto_search_skips_short_confirmations():
    assert should_auto_search_user_text("no") is False
    assert should_auto_search_user_text("Yes.") is False
    assert should_auto_search_user_text("Oh, stop.") is False
    assert should_auto_search_user_text("I") is False
    assert should_auto_search_user_text("What is Reliance Industries?") is True
    assert should_auto_search_user_text("who founded reliance") is True


def test_should_auto_search_skips_stop_signal_in_any_position():
    # Interrupt phrases that contain a stop-signal word should not trigger RAG.
    assert should_auto_search_user_text("Good. Stop. Stop.") is False
    assert should_auto_search_user_text("Good stop") is False
    assert should_auto_search_user_text("Bye for now") is False


def test_document_prefetch_cache_reuses_inflight_task():
    import asyncio

    async def slow_prefetch() -> str:
        await asyncio.sleep(0.05)
        return "cached context"

    async def _run() -> None:
        cache = DocumentPrefetchCache()
        cache.schedule("revenue", slow_prefetch())
        result = await cache.consume("revenue")
        assert result == "cached context"
        assert await cache.consume("revenue") == "cached context"

    asyncio.run(_run())


def test_filter_relevant_hits_drops_weak_matches():
    hits = [
        RagSearchHit(text="strong", score=0.62, source_uri="a.txt"),
        RagSearchHit(text="weak", score=0.18, source_uri="b.txt"),
    ]
    filtered = filter_relevant_hits(hits, min_score=0.3)
    assert len(filtered) == 1
    assert filtered[0].text == "strong"


def test_requires_sync_turn_completion_when_qdrant_backend():
    config = ClientConfig(
        phone_number="911171366880",
        client_name="Test Client",
        xai_collection_id="phone_911171366880",
        rag_backend="qdrant",
    )
    assert requires_sync_turn_completion(config) is True


def test_requires_sync_turn_completion_false_without_qdrant():
    config = ClientConfig(
        phone_number="911171366880",
        client_name="Test Client",
        xai_collection_id="collection-1",
        rag_backend="xai",
    )
    assert requires_sync_turn_completion(config) is False


def test_build_prefetched_context_message_includes_excerpts():
    message = build_prefetched_context_message(
        user_query="revenue",
        hits=[
            RagSearchHit(
                text="Annual revenues were US$ 10.1 billion.",
                score=0.9,
                source_uri="reliance.pdf",
            )
        ],
    )
    assert "Uploaded document search results" in message
    assert "Annual revenues" in message
    assert "uploaded documents" in message.lower()
