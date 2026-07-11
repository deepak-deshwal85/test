import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from session_greeting import GREETING_INSTRUCTIONS, greet_caller, is_session_closing_error


def test_is_session_closing_error():
    assert is_session_closing_error(
        RuntimeError("AgentSession is closing, cannot use generate_reply()")
    )
    assert not is_session_closing_error(RuntimeError("something else"))
    assert not is_session_closing_error(ValueError("AgentSession is closing"))


@pytest.mark.asyncio
async def test_greet_caller_success():
    session = MagicMock()
    session.generate_reply = AsyncMock()
    assert await greet_caller(session, greeting_instructions=GREETING_INSTRUCTIONS) is True
    session.generate_reply.assert_awaited_once()


@pytest.mark.asyncio
async def test_greet_caller_skips_when_session_closing():
    session = MagicMock()
    session.generate_reply = AsyncMock(
        side_effect=RuntimeError("AgentSession is closing, cannot use generate_reply()")
    )
    assert await greet_caller(session, greeting_instructions=GREETING_INSTRUCTIONS) is False
