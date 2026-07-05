from __future__ import annotations

import logging
import os
import re

from client_config import ClientConfig
from rag_client.api_retriever import create_api_rag_retriever
from rag_client.config import RagClientSettings, load_rag_settings, resolve_rag_backend
from rag_client.models import RagSearchHit, format_search_hits

logger = logging.getLogger("agent-telephone-agent")

SKIP_AUTO_SEARCH_PHRASES = frozenset(
    {
        "no",
        "nope",
        "yes",
        "yeah",
        "yep",
        "ok",
        "okay",
        "thanks",
        "thank you",
        "stop",
        "bye",
        "goodbye",
        "hi",
        "hello",
    }
)


def create_knowledge_retriever(
    client_config: ClientConfig,
    settings: RagClientSettings | None = None,
):
    rag_settings = settings or load_rag_settings()
    backend = resolve_rag_backend(client_config, rag_settings)
    if backend != "qdrant":
        return None

    return create_api_rag_retriever(
        client_config=client_config,
        settings=rag_settings,
    )


def extract_message_text(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""

    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
        elif hasattr(item, "text"):
            parts.append(str(item.text))
    return " ".join(parts).strip()


def should_auto_search_user_text(user_text: str) -> bool:
    normalized = re.sub(r"[^\w\s]", "", user_text.strip().lower())
    normalized = " ".join(normalized.split())
    if not normalized:
        return False
    return normalized not in SKIP_AUTO_SEARCH_PHRASES


def build_prefetched_context_message(*, user_query: str, hits: list[RagSearchHit]) -> str:
    if hits:
        excerpts = format_search_hits(hits)
        return (
            f"Uploaded document search results for the caller's question ({user_query!r}):\n"
            f"{excerpts}\n"
            "Answer using these excerpts when they are relevant. "
            "If they do not contain the answer, say you do not have that detail "
            "in the uploaded documents."
        )

    return (
        f"Uploaded document search results for the caller's question ({user_query!r}):\n"
        "No matching information was found in the knowledge base.\n"
        "Tell the caller you do not have that detail in the uploaded documents."
    )


def requires_sync_turn_completion(client_config: ClientConfig) -> bool:
    """RAG prefetch in on_user_turn_completed must finish before the LLM runs."""
    return create_knowledge_retriever(client_config) is not None


async def prefetch_uploaded_documents(
    *,
    client_config: ClientConfig,
    user_text: str,
    retriever,
    settings: RagClientSettings | None = None,
) -> str | None:
    if not should_auto_search_user_text(user_text):
        return None

    rag_settings = settings or load_rag_settings()
    max_results = int(os.getenv("RAG_MAX_RESULTS", str(rag_settings.max_results)))
    hits = await retriever.search(user_text, max_results=max_results)
    top_score = max((hit.score for hit in hits), default=0.0)
    logger.info(
        "auto document search phone=%s query=%r hits=%d top_score=%.3f",
        client_config.phone_number,
        user_text[:80],
        len(hits),
        top_score,
    )
    return build_prefetched_context_message(user_query=user_text, hits=hits)
