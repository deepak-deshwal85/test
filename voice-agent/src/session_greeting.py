from __future__ import annotations

import logging

from livekit.agents import AgentSession

logger = logging.getLogger("relaydesk-agent")

GREETING_INSTRUCTIONS = (
    "Greet the caller briefly. Introduce the business and summarize key service "
    "offerings. Say you can answer questions by searching the uploaded documents. "
    "Ask what they would like to know."
)


def is_session_closing_error(exc: BaseException) -> bool:
    return isinstance(exc, RuntimeError) and "AgentSession is closing" in str(exc)


async def greet_caller(session: AgentSession, *, greeting_instructions: str) -> bool:
    """Speak the opening greeting. Returns False if the call ended first."""
    instructions = greeting_instructions.strip()
    if not instructions:
        logger.warning("empty greeting instructions; skipping greeting")
        return False
    try:
        await session.generate_reply(
            instructions=instructions,
            allow_interruptions=True,
        )
        return True
    except RuntimeError as exc:
        if is_session_closing_error(exc):
            logger.info("skipping greeting: session ended before reply could start")
            return False
        raise
