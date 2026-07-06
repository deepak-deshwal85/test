import logging

from livekit.agents import ToolError, function_tool

from client_config import ClientConfig
from meeting_scheduler import (
    MeetingRequest,
    book_meeting,
    get_meeting_availability,
)

logger = logging.getLogger("relaydesk-agent")


def build_meeting_scheduling_instructions(client_name: str) -> str:
    return f"""# Meeting scheduling tools

- You CAN book meetings with schedule_meeting and get_available_meeting_slots.
- When the caller is done with resume questions, offer a meeting with {client_name}.
- Ask for a preferred date, call get_available_meeting_slots, offer times, collect name and email.
- Convert spoken emails, for example "name at gmail dot com" becomes name@gmail.com.
- Confirm details, call schedule_meeting, then confirm the booking to the caller."""


def build_scheduling_tools(
    client_config: ClientConfig,
    *,
    default_timezone: str,
) -> list[object]:
    if client_config.calcom is None:
        logger.warning(
            "Cal.com is not configured for phone %s; scheduling tools disabled",
            client_config.phone_number,
        )
        return []

    calcom = client_config.calcom

    @function_tool(
        name="get_available_meeting_slots",
        description=(
            "REQUIRED for meeting scheduling. Returns real open Cal.com times "
            "between start_date and end_date (YYYY-MM-DD). Call this before "
            "offering or confirming a meeting time."
        ),
    )
    async def get_available_meeting_slots(
        start_date: str,
        end_date: str,
        timezone: str = default_timezone,
    ) -> str:
        try:
            return await get_meeting_availability(
                calcom,
                start_date=start_date,
                end_date=end_date,
                timezone=timezone or default_timezone,
            )
        except ValueError as exc:
            raise ToolError(str(exc)) from exc

    @function_tool(
        name="schedule_meeting",
        description=(
            "REQUIRED to book a meeting on Cal.com after the caller confirms their "
            "name, email, date, and time. Never say you cannot book; use this tool."
        ),
    )
    async def schedule_meeting(
        attendee_name: str,
        attendee_email: str,
        meeting_date: str,
        meeting_time: str,
        timezone: str = default_timezone,
        notes: str = "",
    ) -> str:
        try:
            return await book_meeting(
                MeetingRequest(
                    client_phone_number=client_config.phone_number,
                    client_name=client_config.client_name,
                    attendee_name=attendee_name,
                    attendee_email=attendee_email,
                    meeting_date=meeting_date,
                    meeting_time=meeting_time,
                    timezone=timezone or default_timezone,
                    notes=notes,
                ),
                calcom,
            )
        except ValueError as exc:
            raise ToolError(str(exc)) from exc

    logger.info(
        "enabled Cal.com scheduling tools for %s (%s/%s)",
        client_config.client_name,
        calcom.username,
        calcom.event_type_slug,
    )
    return [get_available_meeting_slots, schedule_meeting]
