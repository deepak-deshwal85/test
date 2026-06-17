import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from livekit import rtc

from rag import RagChunk, RagStore
from sip_utils import extract_routing_phone_number


class _FakeParticipant:
    def __init__(self, attributes: dict[str, str]):
        self.kind = rtc.ParticipantKind.PARTICIPANT_KIND_SIP
        self.attributes = attributes


def test_extract_routing_phone_number_prefers_trunk_number():
    participant = _FakeParticipant(
        {
            "sip.trunkPhoneNumber": "+1 (555) 123-1234",
            "sip.phoneNumber": "+1 (555) 999-9999",
        }
    )
    assert extract_routing_phone_number(participant) == "15551231234"


def test_extract_routing_phone_number_falls_back_to_caller_number():
    participant = _FakeParticipant({"sip.phoneNumber": "6789"})
    assert extract_routing_phone_number(participant) == "6789"


def test_rag_store_answer_includes_retrieved_context():
    store = RagStore(
        model_name="test-model",
        chunks=[RagChunk(text="Available Tuesday mornings.", embedding=[1.0, 0.0])],
        embed_query=lambda _text: [1.0, 0.0],
    )
    answer = store.answer("When are you available?")
    assert "Tuesday mornings" in answer
    assert "resume" in answer.lower()
