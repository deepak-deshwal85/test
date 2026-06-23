import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agent_instructions import build_conversation_flow_instructions


def test_conversation_flow_requires_uploaded_documents():
    instructions = build_conversation_flow_instructions(
        "Deepak Kumar",
        knowledge_search_tool="search_knowledge_base",
    )
    assert "uploaded documents" in instructions.lower()
    assert "automatically searches uploaded documents" in instructions.lower()
    assert "search_knowledge_base" in instructions
    assert "schedule a meeting" in instructions.lower()
    assert "do not say goodbye" in instructions.lower()
