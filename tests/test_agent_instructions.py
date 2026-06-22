import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agent_instructions import build_conversation_flow_instructions


def test_conversation_flow_starts_with_resume_questions():
    instructions = build_conversation_flow_instructions("Deepak Kumar")
    assert "uploaded documents" in instructions.lower()
    assert "Deepak Kumar" in instructions
    assert "schedule a meeting" in instructions.lower()
    assert "do not say goodbye" in instructions.lower()
