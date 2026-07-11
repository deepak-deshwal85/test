from __future__ import annotations

from livekit.agents import llm

from rag_client.prefetch import extract_message_text

MAX_SUMMARY_LENGTH = 8000


def build_call_summary_from_history(history: llm.ChatContext) -> str:
    lines: list[str] = []
    for message in history.items:
        if message.role not in {"user", "assistant"}:
            continue
        text = extract_message_text(message.content).strip()
        if not text:
            continue
        speaker = "Caller" if message.role == "user" else "Agent"
        lines.append(f"{speaker}: {text}")

    if not lines:
        return "Call completed with no transcript captured."

    transcript = "\n".join(lines)
    if len(transcript) > MAX_SUMMARY_LENGTH:
        return transcript[:MAX_SUMMARY_LENGTH] + "…"
    return transcript
