import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from call_summary_builder import build_call_summary_from_history
from livekit.agents import llm
from rag_client.call_summary_client import CallSummaryApiClient


def test_build_call_summary_from_history():
    history = llm.ChatContext()
    history.add_message(role="assistant", content="Hello, how can I help?")
    history.add_message(role="user", content="What are your hours?")
    history.add_message(role="assistant", content="We are open 9 to 5.")

    summary = build_call_summary_from_history(history)
    assert "Caller: What are your hours?" in summary
    assert "Agent: We are open 9 to 5." in summary


def test_call_summary_api_client_posts_record():
    captured: dict[str, object] = {}
    start = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    end = datetime(2026, 1, 1, 10, 5, tzinfo=UTC)

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(201, json={"id": 1})

    transport = httpx.MockTransport(handler)

    async def _run() -> None:
        client = httpx.AsyncClient(transport=transport, base_url="http://api.test")
        api_client = CallSummaryApiClient(
            base_url="http://api.test",
            http_client=client,
        )
        await api_client.create_call_summary(
            customer_id=14,
            call_start_time=start,
            call_end_time=end,
            call_summary="Caller asked about hours.",
            job_id=UUID("aaaaaaaa-bbbb-cccc-dddd-000000000001"),
        )
        assert captured["path"] == "/v1/call-summaries"
        payload = captured["payload"]
        assert payload["customer_id"] == 14
        assert payload["call_summary"] == "Caller asked about hours."
        await api_client.aclose()

    import asyncio

    asyncio.run(_run())
