import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from call_summary_builder import (
    CallTranscriptCollector,
    build_call_summary_from_collector,
    build_call_summary_from_history,
    format_conversation_line,
    message_text,
)
from livekit.agents import llm
from livekit.agents.llm.chat_context import AgentHandoff


def test_build_call_summary_from_history():
    history = llm.ChatContext()
    history.add_message(role="assistant", content="Hello, how can I help?")
    history.add_message(role="user", content="What are your hours?")
    history.add_message(role="assistant", content="We are open 9 to 5.")

    summary = build_call_summary_from_history(history)
    assert "Caller: What are your hours?" in summary
    assert "Agent: We are open 9 to 5." in summary


def test_build_call_summary_skips_agent_handoff_items():
    history = llm.ChatContext()
    history.add_message(role="user", content="Hello?")
    history.insert(
        AgentHandoff(
            old_agent_id="agent-a",
            new_agent_id="agent-b",
        )
    )
    history.add_message(role="assistant", content="Hi, I can help with that.")

    summary = build_call_summary_from_history(history)
    assert "Caller: Hello?" in summary
    assert "Agent: Hi, I can help with that." in summary
    assert "agent-a" not in summary


def test_collector_deduplicates_by_message_id():
    history = llm.ChatContext()
    history.add_message(role="user", content="First question")
    history.add_message(role="assistant", content="First answer")

    collector = CallTranscriptCollector()
    collector.extend_from_context(history)
    collector.extend_from_context(history)

    summary = build_call_summary_from_collector(collector)
    assert summary.count("Caller: First question") == 1
    assert summary.count("Agent: First answer") == 1


def test_message_text_uses_text_content():
    history = llm.ChatContext()
    history.add_message(role="user", content="Spoken transcript")
    message = history.items[0]
    assert message_text(message) == "Spoken transcript"
    assert format_conversation_line(message) == "Caller: Spoken transcript"


def test_collector_merges_session_and_agent_histories():
    session_history = llm.ChatContext()
    session_history.add_message(role="user", content="Question from session")

    agent_history = llm.ChatContext()
    agent_history.add_message(role="assistant", content="Answer from agent")

    collector = CallTranscriptCollector()
    summary = build_call_summary_from_collector(
        collector,
        session_history,
        agent_history,
    )
    assert "Caller: Question from session" in summary
    assert "Agent: Answer from agent" in summary


def test_call_summary_api_client_posts_record():
    import asyncio
    import json
    from datetime import UTC, datetime
    from uuid import UUID

    import httpx

    from rag_client.call_summary_client import CallSummaryApiClient

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
            call_summary="Caller: What are your hours?\nAgent: Nine to five.",
            job_id=UUID("aaaaaaaa-bbbb-cccc-dddd-000000000001"),
        )
        assert captured["path"] == "/v1/call-summaries"
        payload = captured["payload"]
        assert payload["customer_id"] == 14
        assert "Caller: What are your hours?" in str(payload["call_summary"])
        await api_client.aclose()

    asyncio.run(_run())
