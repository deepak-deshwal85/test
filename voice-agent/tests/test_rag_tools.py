import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from client_config import ClientConfig
from rag_client.config import RagClientSettings
from rag_client.models import RagSearchHit, format_search_hits
from rag_client.tools import (
    build_rag_instructions,
    build_rag_tools,
    knowledge_search_tool_label,
)


class FakeApiRetriever:
    async def search(self, query: str, *, max_results: int) -> list[RagSearchHit]:
        return [
            RagSearchHit(
                text=f"Answer for {query}",
                score=0.9,
                source_uri="resume.pdf",
            )
        ]


def test_knowledge_search_tool_label_switches_by_backend():
    assert knowledge_search_tool_label("xai") == "file search"
    assert knowledge_search_tool_label("qdrant") == "search_knowledge_base"


def test_build_rag_instructions_mentions_tool_name():
    instructions = build_rag_instructions("qdrant")
    assert "search_knowledge_base" in instructions
    assert "uploaded documents" in instructions.lower()


def test_build_rag_tools_uses_qdrant_function_tool():
    client = ClientConfig(
        phone_number="911171366880",
        client_name="Deepak Kumar",
        xai_collection_id="collection_test",
        client_email_id="client@example.com",
        rag_backend="qdrant",
    )
    settings = RagClientSettings(
        backend="qdrant",
        max_results=3,
        rag_api_base_url="http://127.0.0.1:8090",
        min_score=0.3,
    )

    def factory(*, client_config, settings):
        assert client_config.phone_number == "911171366880"
        return FakeApiRetriever()

    tools = build_rag_tools(client, settings=settings, api_retriever_factory=factory)
    assert len(tools) == 1
    assert tools[0].id == "search_knowledge_base"


def test_format_search_hits_returns_plain_language():
    message = format_search_hits(
        [RagSearchHit(text="Built RAG pipelines.", score=0.8, source_uri="reliance.pdf")]
    )
    assert "Relevant document excerpts" in message
    assert "Built RAG pipelines." in message
