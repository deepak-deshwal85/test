import json
import logging
import os
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from calcom_client import CalComClient, CalComError, CalComEventConfig
from client_config import CalComConfig
from paths import MEETINGS_DIR

logger = logging.getLogger("agent-telephone-agent")

DEFAULT_MEETINGS_FILE = MEETINGS_DIR / "scheduled_meetings.jsonl"
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SLOT_MATCH_TOLERANCE = timedelta(minutes=1)
SPOKEN_EMAIL_AT = re.compile(r"\s+at the rate of\s+", re.IGNORECASE)
SPOKEN_EMAIL_DOT = re.compile(r"\s+dot\s+", re.IGNORECASE)


@dataclass(frozen=True)
class MeetingRequest:
    client_phone_number: str
    client_name: str
    attendee_name: str
    attendee_email: str
    meeting_date: str
    meeting_time: str
    timezone: str
    notes: str = ""


def normalize_spoken_email(email: str) -> str:
    normalized = email.strip()
    normalized = SPOKEN_EMAIL_AT.sub("@", normalized)
    normalized = SPOKEN_EMAIL_DOT.sub(".", normalized)
    normalized = re.sub(r"\s+", "", normalized)
    return normalized.lower()


def _parse_meeting_datetime(
    meeting_date: str, meeting_time: str, timezone: str
) -> datetime:
    try:
        tz = ZoneInfo(timezone)
    except Exception as exc:
        raise ValueError(f"Invalid timezone: {timezone}") from exc

    try:
        naive = datetime.strptime(f"{meeting_date} {meeting_time}", "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise ValueError(
            "Meeting date must be YYYY-MM-DD and meeting time must be HH:MM in 24-hour format."
        ) from exc

    return naive.replace(tzinfo=tz)


def _format_meeting_datetime(meeting_at: datetime) -> str:
    return meeting_at.strftime("%A, %B %d, %Y at %I:%M %p %Z")


def _validate_request(request: MeetingRequest) -> datetime:
    attendee_name = request.attendee_name.strip()
    attendee_email = normalize_spoken_email(request.attendee_email)
    if not attendee_name:
        raise ValueError("Attendee name is required.")
    if not EMAIL_PATTERN.match(attendee_email):
        raise ValueError("A valid attendee email is required.")

    return _parse_meeting_datetime(
        request.meeting_date.strip(),
        request.meeting_time.strip(),
        request.timezone.strip(),
    )


def _ensure_future(meeting_at: datetime, now: datetime | None = None) -> None:
    reference_time = now or datetime.now(tz=meeting_at.tzinfo)
    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=meeting_at.tzinfo)
    else:
        reference_time = reference_time.astimezone(meeting_at.tzinfo)

    if meeting_at <= reference_time:
        raise ValueError("Meeting date and time must be in the future.")


def _to_calcom_config(config: CalComConfig) -> CalComEventConfig:
    return CalComEventConfig(
        username=config.username,
        event_type_slug=config.event_type_slug,
        event_type_id=config.event_type_id,
        organization_slug=config.organization_slug,
    )


def _slot_matches(requested_utc: datetime, available_utc: datetime) -> bool:
    return abs(requested_utc - available_utc) <= SLOT_MATCH_TOLERANCE


def _persist_booking_record(record: dict[str, object], meetings_file: Path) -> None:
    meetings_file.parent.mkdir(parents=True, exist_ok=True)
    with meetings_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def format_available_slots(
    slots: list[datetime],
    timezone: str,
    *,
    limit: int = 6,
) -> str:
    if not slots:
        return (
            "No available meeting times were found for those dates. "
            "Ask the caller for another date."
        )

    tz = ZoneInfo(timezone)
    formatted = [
        _format_meeting_datetime(slot.astimezone(tz)) for slot in slots[:limit]
    ]
    if len(slots) > limit:
        formatted.append(f"and {len(slots) - limit} more options")
    return "Available times: " + "; ".join(formatted) + "."


def create_calcom_client() -> CalComClient:
    return CalComClient(
        api_key=os.getenv("CALCOM_API_KEY", "").strip() or None,
        base_url=os.getenv("CALCOM_BASE_URL", "https://api.cal.com"),
        api_version=os.getenv("CALCOM_API_VERSION", "2024-09-04"),
    )


async def get_meeting_availability(
    calcom_config: CalComConfig,
    *,
    start_date: str,
    end_date: str,
    timezone: str,
    calcom_client: CalComClient | None = None,
) -> str:
    client = calcom_client or create_calcom_client()
    owns_client = calcom_client is None
    try:
        slots = await client.fetch_available_slots(
            _to_calcom_config(calcom_config),
            start_date=start_date,
            end_date=end_date,
            timezone=timezone,
        )
    except CalComError as exc:
        raise ValueError(
            f"{exc}. Verify calcom_event_type_slug in the phone config matches "
            f"your Cal.com booking link."
        ) from exc
    finally:
        if owns_client:
            await client.aclose()
    return format_available_slots(slots, timezone)


async def book_meeting(
    request: MeetingRequest,
    calcom_config: CalComConfig,
    *,
    meetings_file: Path = DEFAULT_MEETINGS_FILE,
    now: datetime | None = None,
    calcom_client: CalComClient | None = None,
) -> str:
    meeting_at = _validate_request(request)
    _ensure_future(meeting_at, now=now)
    requested_utc = meeting_at.astimezone(UTC)
    normalized_email = normalize_spoken_email(request.attendee_email)

    client = calcom_client or create_calcom_client()
    owns_client = calcom_client is None
    event_config = _to_calcom_config(calcom_config)
    skip_slot_check = os.getenv("CALCOM_SKIP_SLOT_CHECK", "").lower() in {
        "1",
        "true",
        "yes",
    }

    try:
        if not skip_slot_check:
            day_start = meeting_at.date().isoformat()
            day_end = (meeting_at.date() + timedelta(days=1)).isoformat()
            try:
                available_slots = await client.fetch_available_slots(
                    event_config,
                    start_date=day_start,
                    end_date=day_end,
                    timezone=request.timezone.strip(),
                )
            except CalComError as exc:
                logger.warning(
                    "Cal.com slot lookup failed, attempting direct booking: %s", exc
                )
                available_slots = []
            if available_slots and not any(
                _slot_matches(requested_utc, slot) for slot in available_slots
            ):
                raise ValueError(
                    "That time is not available. Check availability and offer another slot."
                )

        booking = await client.create_booking(
            event_config,
            start_utc=requested_utc,
            attendee_name=request.attendee_name.strip(),
            attendee_email=normalized_email,
            timezone=request.timezone.strip(),
            notes=request.notes,
        )
    except CalComError as exc:
        raise ValueError(str(exc)) from exc
    finally:
        if owns_client:
            await client.aclose()

    formatted_time = _format_meeting_datetime(meeting_at)
    record = {
        **asdict(request),
        "attendee_email": normalized_email,
        "meeting_at_iso": meeting_at.isoformat(),
        "scheduled_at_iso": datetime.now(tz=UTC).isoformat(),
        "calcom_booking_uid": booking.booking_uid,
        "calcom_meeting_url": booking.meeting_url,
    }
    _persist_booking_record(record, meetings_file)

    confirmation = (
        f"Meeting scheduled for {request.attendee_name.strip()} with "
        f"{request.client_name} on {formatted_time}. "
        f"A calendar invite will be sent to {normalized_email}."
    )
    if booking.meeting_url:
        confirmation += f" Meeting link: {booking.meeting_url}."
    return confirmation
