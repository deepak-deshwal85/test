from __future__ import annotations

from livekit.agents import llm

from rag_client.prefetch import extract_message_text

MAX_SUMMARY_LENGTH = 8000


def build_call_summary_from_history(history: llm.ChatContext) -> str:
    lines: list[str] = []
    for item in history.items:
        # History may include AgentHandoff and other non-message entries.
        role = getattr(item, "role", None)
        if role not in {"user", "assistant"}:
            continue
        content = getattr(item, "content", None)
        if content is None:
            continue
        text = extract_message_text(content).strip()
        if not text:
            continue
        speaker = "Caller" if role == "user" else "Agent"
        lines.append(f"{speaker}: {text}")

    if not lines:
        return "Call completed with no transcript captured."

    transcript = "\n".join(lines)
    if len(transcript) > MAX_SUMMARY_LENGTH:
        return transcript[:MAX_SUMMARY_LENGTH] + "…"
    return transcript
