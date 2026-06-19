import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from livekit import rtc

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
