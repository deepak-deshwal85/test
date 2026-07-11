from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

from livekit.agents import llm

from rag_client.prefetch import extract_message_text

logger = logging.getLogger("relaydesk-agent")

MAX_SUMMARY_LENGTH = 8000
EMPTY_TRANSCRIPT_MESSAGE = "Call completed with no transcript captured."


class _HasChatItems(Protocol):
    @property
    def items(self) -> list[object]: ...


@dataclass
class CallTranscriptCollector:
    """Accumulates caller/agent lines as the session emits conversation items."""

    _lines: list[str] = field(default_factory=list)
    _seen_message_ids: set[str] = field(default_factory=set)

    def add_item(self, item: object) -> None:
        line = format_conversation_line(item)
        if line is None:
            return

        message_id = getattr(item, "id", None)
        if isinstance(message_id, str) and message_id:
            if message_id in self._seen_message_ids:
                return
            self._seen_message_ids.add(message_id)

        self._lines.append(line)

    def extend_from_context(self, history: _HasChatItems | None) -> None:
        if history is None:
            return
        for item in history.items:
            self.add_item(item)

    @property
    def lines(self) -> list[str]:
        return list(self._lines)


def message_text(item: object) -> str:
    text_content = getattr(item, "text_content", None)
    if isinstance(text_content, str) and text_content.strip():
        return text_content.strip()

    content = getattr(item, "content", None)
    if content is not None:
        extracted = extract_message_text(content).strip()
        if extracted:
            return extracted
    return ""


def format_conversation_line(item: object) -> str | None:
    role = getattr(item, "role", None)
    if role not in {"user", "assistant"}:
        return None

    text = message_text(item)
    if not text:
        return None

    speaker = "Caller" if role == "user" else "Agent"
    return f"{speaker}: {text}"


def setup_call_transcript_collector(
    session: object,
    collector: CallTranscriptCollector,
) -> None:
    from livekit.agents.voice.events import ConversationItemAddedEvent

    @session.on("conversation_item_added")
    def _on_conversation_item(ev: ConversationItemAddedEvent) -> None:
        collector.add_item(ev.item)


def build_call_transcript_from_collector(
    collector: CallTranscriptCollector,
    *histories: _HasChatItems | None,
) -> str:
    """Build the raw Caller/Agent transcript from collected session events."""
    for history in histories:
        collector.extend_from_context(history)

    if not collector.lines:
        logger.warning(
            "call transcript empty after session ended (history fallbacks=%d)",
            len(histories),
        )
        return EMPTY_TRANSCRIPT_MESSAGE

    transcript = "\n".join(collector.lines)
    if len(transcript) > MAX_SUMMARY_LENGTH:
        return transcript[:MAX_SUMMARY_LENGTH] + "…"
    return transcript


def build_call_summary_from_collector(
    collector: CallTranscriptCollector,
    *histories: _HasChatItems | None,
) -> str:
    """Return raw transcript (legacy name). Prefer build_call_transcript_from_collector."""
    return build_call_transcript_from_collector(collector, *histories)


def build_call_summary_from_history(history: llm.ChatContext | _HasChatItems) -> str:
    collector = CallTranscriptCollector()
    collector.extend_from_context(history)
    return build_call_summary_from_collector(collector)
