import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from rag_client.api_retriever import ApiRagRetriever
from rag_client.config import RagClientSettings


def test_api_rag_retriever_calls_search_endpoint():
    settings = RagClientSettings(
        backend="qdrant",
        max_results=3,
        rag_api_base_url="http://rag.test",
        min_score=0.3,
    )
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "hits": [
                    {
                        "text": "Python engineer with RAG experience.",
                        "score": 0.91,
                        "source_uri": "resume.pdf",
                    }
                ],
                "count": 1,
            },
        )

    transport = httpx.MockTransport(handler)

    async def _run() -> None:
        client = httpx.AsyncClient(transport=transport, base_url="http://rag.test")
        retriever = ApiRagRetriever(
            base_url="http://rag.test",
            phone_number="911171366880",
            settings=settings,
            http_client=client,
        )
        hits = await retriever.search("What are Deepak's skills?", max_results=3)
        assert captured["path"] == "/v1/search"
        assert captured["payload"]["phone_number"] == "911171366880"
        assert hits[0].text.startswith("Python engineer")
        await retriever.aclose()

    import asyncio

    asyncio.run(_run())
