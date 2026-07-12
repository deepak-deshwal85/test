import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from livekit.agents import llm

from agent import _CallSummarySessionState, _finalize_call_summary
from call_summary_builder import CallTranscriptCollector


@pytest.mark.asyncio
async def test_finalize_call_summary_persists_after_session_history_populated():
    history = llm.ChatContext()
    history.add_message(role="user", content="Who delivered the judgment?")
    history.add_message(
        role="assistant",
        content="Justice D.Y. Chandrachud delivered the judgment.",
    )

    collector = CallTranscriptCollector()
    collector.extend_from_context(history)

    captured: dict[str, object] = {}
    mock_client = AsyncMock()
    mock_client.aclose = AsyncMock()

    async def _capture_persist(**kwargs):
        captured.update(kwargs)

    mock_ctx = SimpleNamespace(
        proc=SimpleNamespace(
            userdata={
                "consumer_id": 14,
                "job_id": UUID("d62cf7c6-8395-4135-801a-261660fe3662"),
                "call_outcome": {"meeting_scheduled": False},
            }
        )
    )

    state = _CallSummarySessionState(
        call_start_time=datetime(2026, 7, 12, 6, 41, 18, tzinfo=UTC),
        transcript_collector=collector,
        session=SimpleNamespace(history=history),
        agent=SimpleNamespace(_chat_ctx=history),
        client_config=SimpleNamespace(client_name="ABC company"),
        call_summary_client=mock_client,
        ctx=mock_ctx,
    )

    import agent as agent_module

    original_persist = agent_module.persist_call_summary
    original_summarize = agent_module.summarize_call_transcript
    agent_module.persist_call_summary = _capture_persist
    agent_module.summarize_call_transcript = AsyncMock(
        return_value="Caller asked who delivered the judgment and the agent answered."
    )
    try:
        await _finalize_call_summary(state, reason="participant_disconnected")
    finally:
        agent_module.persist_call_summary = original_persist
        agent_module.summarize_call_transcript = original_summarize

    assert captured["consumer_id"] == 14
    assert "Caller asked who delivered the judgment" in str(captured["call_summary"])
    mock_client.aclose.assert_awaited_once()
