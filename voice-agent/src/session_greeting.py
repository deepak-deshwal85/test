from __future__ import annotations

import logging

from livekit.agents import AgentSession

logger = logging.getLogger("relaydesk-agent")

GREETING_INSTRUCTIONS = (
    "Greet the caller briefly. Say you can answer questions from "
    "the uploaded documents. Ask what they would like to know."
)


def is_session_closing_error(exc: BaseException) -> bool:
    return isinstance(exc, RuntimeError) and "AgentSession is closing" in str(exc)


async def greet_caller(session: AgentSession) -> bool:
    """Speak the opening greeting. Returns False if the call ended first."""
    try:
        await session.generate_reply(
            instructions=GREETING_INSTRUCTIONS,
            allow_interruptions=True,
        )
        return True
    except RuntimeError as exc:
        if is_session_closing_error(exc):
            logger.info("skipping greeting: session ended before reply could start")
            return False
        raise
