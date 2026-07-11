import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from call_summary_builder import EMPTY_TRANSCRIPT_MESSAGE
from call_summary_llm import summarize_call_transcript
from livekit.agents.llm import CollectedResponse


@pytest.mark.asyncio
async def test_summarize_call_transcript_uses_llm():
    mock_llm = MagicMock()
    mock_stream = MagicMock()
    mock_stream.collect = AsyncMock(
        return_value=CollectedResponse(
            text=(
                "The caller asked about pricing and onboarding. "
                "The agent answered from uploaded documents. "
                "No meeting was scheduled."
            )
        )
    )
    mock_llm.chat.return_value = mock_stream
    mock_llm.aclose = AsyncMock()

    transcript = (
        "Caller: What are your prices?\n"
        "Agent: Our starter plan is listed in the uploaded documents."
    )
    summary = await summarize_call_transcript(
        transcript,
        client_name="Acme Support",
        meeting_scheduled=False,
        llm_instance=mock_llm,
    )

    assert "pricing" in summary.lower() or "caller" in summary.lower()
    mock_llm.chat.assert_called_once()
    mock_llm.aclose.assert_not_called()


@pytest.mark.asyncio
async def test_summarize_call_transcript_skips_llm_when_empty():
    mock_llm = MagicMock()
    summary = await summarize_call_transcript(
        EMPTY_TRANSCRIPT_MESSAGE,
        llm_instance=mock_llm,
    )
    assert summary == EMPTY_TRANSCRIPT_MESSAGE
    mock_llm.chat.assert_not_called()


@pytest.mark.asyncio
async def test_summarize_call_transcript_falls_back_to_transcript_on_llm_error():
    mock_llm = MagicMock()
    mock_stream = MagicMock()
    mock_stream.collect = AsyncMock(side_effect=RuntimeError("llm unavailable"))
    mock_llm.chat.return_value = mock_stream

    transcript = "Caller: Hello?\nAgent: Hi, how can I help?"
    summary = await summarize_call_transcript(
        transcript,
        llm_instance=mock_llm,
    )
    assert "Caller: Hello?" in summary
