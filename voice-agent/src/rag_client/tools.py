import logging
import os
import time

from livekit.agents import ToolError, function_tool
from livekit.plugins import xai

from client_config import ClientConfig
from rag_client.api_retriever import create_api_rag_retriever
from rag_client.config import (
    RagClientSettings,
    load_rag_settings,
    resolve_rag_api_url,
    resolve_rag_backend,
)
from rag_client.models import filter_relevant_hits, format_search_hits

logger = logging.getLogger("agent-telephone-agent")

XAI_SEARCH_TOOL_LABEL = "file search"
QDRANT_SEARCH_TOOL_NAME = "search_knowledge_base"


def knowledge_search_tool_label(backend: str) -> str:
    if backend == "qdrant":
        return QDRANT_SEARCH_TOOL_NAME
    return XAI_SEARCH_TOOL_LABEL


def build_rag_instructions(backend: str) -> str:
    tool_label = knowledge_search_tool_label(backend)
    return f"""# Uploaded documents (mandatory)

- Uploaded documents are the only source of truth for factual answers.
- The system auto-searches uploaded documents each turn; use the provided excerpts.
- If excerpts are already provided for this turn, do not call {tool_label} again.
- If excerpts are missing or incomplete, call {tool_label} before answering.
- Never say you lack access to uploaded documents.
- If search finds nothing relevant, say you do not have that detail in the uploaded documents."""


def build_xai_file_search(
    client_config: ClientConfig,
    settings: RagClientSettings | None = None,
) -> xai.FileSearch:
    rag_settings = settings or load_rag_settings()
    return xai.FileSearch(
        vector_store_ids=[client_config.xai_collection_id],
        max_num_results=rag_settings.max_results,
    )


def build_rag_tools(
    client_config: ClientConfig,
    *,
    settings: RagClientSettings | None = None,
    api_retriever_factory=create_api_rag_retriever,
    retriever=None,
) -> list[object]:
    rag_settings = settings or load_rag_settings()
    backend = resolve_rag_backend(client_config, rag_settings)

    if backend == "xai":
        logger.info(
            "enabled xAI FileSearch RAG for %s (collection %s)",
            client_config.client_name,
            client_config.xai_collection_id,
        )
        return [build_xai_file_search(client_config, rag_settings)]

    shared_retriever = retriever or api_retriever_factory(
        client_config=client_config,
        settings=rag_settings,
    )
    api_url = resolve_rag_api_url(client_config, rag_settings)

    @function_tool(
        name=QDRANT_SEARCH_TOOL_NAME,
        description=(
            "Searches all uploaded documents via the RAG API. Call this for any "
            "factual question when document excerpts were not already provided "
            "or you need a follow-up search."
        ),
    )
    async def search_knowledge_base(query: str) -> str:
        tool_started = time.perf_counter()
        try:
            raw_hits = await shared_retriever.search(
                query,
                max_results=int(
                    os.getenv("RAG_MAX_RESULTS", str(rag_settings.max_results))
                ),
            )
            hits = filter_relevant_hits(raw_hits, min_score=rag_settings.min_score)
            logger.info(
                "search_knowledge_base tool_ms=%.0f query=%r hits=%d raw_hits=%d",
                (time.perf_counter() - tool_started) * 1000,
                query[:80],
                len(hits),
                len(raw_hits),
            )
            return format_search_hits(hits)
        except Exception as exc:
            logger.warning(
                "search_knowledge_base failed after %.0fms: %s",
                (time.perf_counter() - tool_started) * 1000,
                exc,
            )
            raise ToolError(str(exc)) from exc

    logger.info(
        "enabled RAG API search for %s (api=%s)",
        client_config.client_name,
        api_url,
    )
    return [search_knowledge_base]
