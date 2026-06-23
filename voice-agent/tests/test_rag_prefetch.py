import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rag_client.models import RagSearchHit
from rag_client.prefetch import (
    build_prefetched_context_message,
    extract_message_text,
    should_auto_search_user_text,
)


def test_extract_message_text_from_string_list():
    assert extract_message_text(["What is Reliance revenue?"]) == (
        "What is Reliance revenue?"
    )


def test_should_auto_search_skips_short_confirmations():
    assert should_auto_search_user_text("no") is False
    assert should_auto_search_user_text("Yes.") is False
    assert should_auto_search_user_text("What is Reliance Industries?") is True


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
