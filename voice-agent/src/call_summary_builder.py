from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

from livekit.agents import llm
from livekit.agents.llm.chat_context import AudioContent, ChatMessage

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
        message_id = getattr(item, "id", None)
        if (
            isinstance(message_id, str)
            and message_id
            and message_id in self._seen_message_ids
        ):
            return

        line = format_conversation_line(item)
        if line is None:
            return

        if isinstance(message_id, str) and message_id:
            self._seen_message_ids.add(message_id)

        self._append_line(line)

    def add_user_transcript(self, text: str) -> None:
        """Capture final STT text before it is committed to session history."""
        normalized = text.strip()
        if not normalized:
            return
        self._append_line(f"Caller: {normalized}")

    def _append_line(self, line: str) -> None:
        if line in self._lines:
            return
        self._lines.append(line)

    def extend_from_context(self, history: _HasChatItems | None) -> None:
        if history is None:
            return
        for item in history.items:
            self.add_item(item)

    @property
    def lines(self) -> list[str]:
        return list(self._lines)


def _content_list_text(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return extract_message_text(content)

    parts: list[str] = []
    for part in content:
        if isinstance(part, str) and part.strip():
            parts.append(part.strip())
        elif isinstance(part, AudioContent):
            transcript = part.transcript
            if isinstance(transcript, str) and transcript.strip():
                parts.append(transcript.strip())
        else:
            piece = extract_message_text(part).strip()
            if piece:
                parts.append(piece)
    return "\n".join(parts)


def message_text(item: object) -> str:
    if isinstance(item, ChatMessage):
        text_content = item.text_content
        if isinstance(text_content, str) and text_content.strip():
            return text_content.strip()
        return _content_list_text(item.content)

    text_content = getattr(item, "text_content", None)
    if isinstance(text_content, str) and text_content.strip():
        return text_content.strip()

    content = getattr(item, "content", None)
    if content is not None:
        extracted = _content_list_text(content).strip()
        if extracted:
            return extracted
    return ""


def format_conversation_line(item: object) -> str | None:
    if not isinstance(item, ChatMessage):
        return None

    if item.role not in {"user", "assistant"}:
        return None

    text = message_text(item)
    if not text:
        return None

    speaker = "Caller" if item.role == "user" else "Agent"
    return f"{speaker}: {text}"


def setup_call_transcript_collector(
    session: object,
    collector: CallTranscriptCollector,
) -> list[object]:
    from livekit.agents.voice.events import (
        ConversationItemAddedEvent,
        UserInputTranscribedEvent,
    )

    handlers: list[object] = []

    @session.on("conversation_item_added")
    def _on_conversation_item(ev: ConversationItemAddedEvent) -> None:
        collector.add_item(ev.item)

    handlers.append(_on_conversation_item)

    @session.on("user_input_transcribed")
    def _on_user_input_transcribed(ev: UserInputTranscribedEvent) -> None:
        if ev.is_final:
            collector.add_user_transcript(ev.transcript)

    handlers.append(_on_user_input_transcribed)
    return handlers


def _describe_history_items(items: list[object]) -> dict[str, int]:
    stats = {
        "total": len(items),
        "messages": 0,
        "user": 0,
        "assistant": 0,
        "with_text": 0,
    }
    for item in items:
        if not isinstance(item, ChatMessage):
            continue
        stats["messages"] += 1
        if item.role == "user":
            stats["user"] += 1
        elif item.role == "assistant":
            stats["assistant"] += 1
        if message_text(item):
            stats["with_text"] += 1
    return stats


def build_call_transcript_from_collector(
    collector: CallTranscriptCollector,
    *histories: _HasChatItems | None,
) -> str:
    """Build the raw Caller/Agent transcript from collected session events."""
    for history in histories:
        collector.extend_from_context(history)

    if not collector.lines:
        history_stats = [
            _describe_history_items(getattr(history, "items", []))
            for history in histories
            if history is not None
        ]
        logger.warning(
            "call transcript empty after session ended (history fallbacks=%d stats=%s)",
            len(histories),
            history_stats,
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
