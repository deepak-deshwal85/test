from livekit import rtc

from client_config import normalize_phone_number


def extract_routing_phone_number(participant: rtc.RemoteParticipant) -> str | None:
    """Return the normalized phone number used to select client config.

    Prefer the dialed trunk number so multiple inbound numbers can route to the
    same agent with different knowledge bases.
    """
    if participant.kind != rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
        return None

    for attribute in ("sip.trunkPhoneNumber", "sip.phoneNumber"):
        raw_value = participant.attributes.get(attribute)
        if raw_value:
            return normalize_phone_number(raw_value)

    return None
