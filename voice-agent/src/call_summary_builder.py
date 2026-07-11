from __future__ import annotations

from livekit.agents import llm
from livekit.agents.llm.chat_context import ChatMessage

from rag_client.prefetch import extract_message_text

MAX_SUMMARY_LENGTH = 8000


def build_call_summary_from_history(history: llm.ChatContext) -> str:
    lines: list[str] = []
    for item in history.items:
        if not isinstance(item, ChatMessage):
            continue
        if item.role not in {"user", "assistant"}:
            continue
        text = extract_message_text(item.content).strip()
        if not text:
            continue
        speaker = "Caller" if item.role == "user" else "Agent"
        lines.append(f"{speaker}: {text}")

    if not lines:
        return "Call completed with no transcript captured."

    transcript = "\n".join(lines)
    if len(transcript) > MAX_SUMMARY_LENGTH:
        return transcript[:MAX_SUMMARY_LENGTH] + "…"
    return transcript
