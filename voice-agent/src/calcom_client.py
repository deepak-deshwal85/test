import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

logger = logging.getLogger("relaydesk-agent")

DEFAULT_CALCOM_BASE_URL = "https://api.cal.com"
DEFAULT_CALCOM_API_VERSION = "2024-09-04"
CALCOM_API_VERSIONS = ("2024-09-04", "2024-08-13", "2024-06-14")


@dataclass(frozen=True)
class CalComEventConfig:
    username: str
    event_type_slug: str
    event_type_id: int | None = None
    organization_slug: str | None = None


@dataclass(frozen=True)
class CalComBookingResult:
    booking_uid: str
    start_utc: datetime
    meeting_url: str | None = None


@dataclass(frozen=True)
class CalComEventType:
    event_type_id: int
    slug: str
    title: str


class CalComError(Exception):
    """Raised when Cal.com returns an error response."""


def _looks_like_date_key(value: str) -> bool:
    return len(value) >= 10 and value[4] == "-" and value[7] == "-"


def _parse_slots_payload(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    data = payload.get("data", {})
    if not isinstance(data, dict):
        return {}

    nested_slots = data.get("slots")
    if isinstance(nested_slots, dict):
        return nested_slots

    if any(_looks_like_date_key(str(key)) for key in data):
        return {
            str(key): value
            for key, value in data.items()
            if _looks_like_date_key(str(key)) and isinstance(value, list)
        }

    return {}


class CalComClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = DEFAULT_CALCOM_BASE_URL,
        api_version: str = DEFAULT_CALCOM_API_VERSION,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._api_version = api_version
        self._http_client = http_client
        self._owns_client = http_client is None

    async def aclose(self) -> None:
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    def _headers(self, api_version: str | None = None) -> dict[str, str]:
        headers = {
            "cal-api-version": api_version or self._api_version,
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def _client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=30.0,
            )
            self._owns_client = True
        return self._http_client

    def _error_message(self, payload: dict[str, Any], response_text: str) -> str:
        error = payload.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error)
        if isinstance(error, str):
            return error
        message = payload.get("message")
        if isinstance(message, str):
            return message
        return response_text or "Unknown Cal.com error"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        api_versions: tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        versions = api_versions or (self._api_version,)
        last_error = "Unknown Cal.com error"

        for version in versions:
            client = await self._client()
            response = await client.request(
                method,
                path,
                params=params,
                json=json,
                headers=self._headers(version),
            )
            payload = response.json() if response.content else {}
            if response.status_code < 400:
                return payload

            last_error = self._error_message(payload, response.text)
            if response.status_code not in {404, 405}:
                break

        raise CalComError(f"Cal.com API error: {last_error}")

    def _event_query_params(
        self,
        config: CalComEventConfig,
        *,
        start_date: str,
        end_date: str,
        timezone: str,
    ) -> dict[str, str]:
        params: dict[str, str] = {
            "start": start_date,
            "end": end_date,
            "timeZone": timezone,
        }
        if config.event_type_id is not None:
            params["eventTypeId"] = str(config.event_type_id)
        else:
            params["eventTypeSlug"] = config.event_type_slug
            params["username"] = config.username
        if config.organization_slug:
            params["organizationSlug"] = config.organization_slug
        return params

    async def fetch_event_types(self, username: str) -> list[CalComEventType]:
        payload = await self._request(
            "GET",
            "/v2/event-types",
            params={"username": username},
            api_versions=CALCOM_API_VERSIONS,
        )
        event_types: list[CalComEventType] = []
        for item in payload.get("data", []):
            event_type_id = item.get("id")
            slug = item.get("slug")
            if event_type_id is None or not slug:
                continue
            event_types.append(
                CalComEventType(
                    event_type_id=int(event_type_id),
                    slug=str(slug),
                    title=str(item.get("title") or slug),
                )
            )
        return event_types

    async def fetch_available_slots(
        self,
        config: CalComEventConfig,
        *,
        start_date: str,
        end_date: str,
        timezone: str,
    ) -> list[datetime]:
        params = self._event_query_params(
            config,
            start_date=start_date,
            end_date=end_date,
            timezone=timezone,
        )
        payload = await self._request(
            "GET",
            "/v2/slots",
            params=params,
            api_versions=CALCOM_API_VERSIONS,
        )
        slots_by_date = _parse_slots_payload(payload)
        available: list[datetime] = []
        for day_slots in slots_by_date.values():
            if not isinstance(day_slots, list):
                continue
            for slot in day_slots:
                if isinstance(slot, str):
                    slot_time = slot
                elif isinstance(slot, dict):
                    slot_time = slot.get("time") or slot.get("start")
                else:
                    continue
                if not slot_time:
                    continue
                parsed = datetime.fromisoformat(str(slot_time).replace("Z", "+00:00"))
                available.append(parsed.astimezone(UTC))
        available.sort()
        return available

    async def create_booking(
        self,
        config: CalComEventConfig,
        *,
        start_utc: datetime,
        attendee_name: str,
        attendee_email: str,
        timezone: str,
        notes: str = "",
    ) -> CalComBookingResult:
        if start_utc.tzinfo is None:
            start_utc = start_utc.replace(tzinfo=UTC)
        else:
            start_utc = start_utc.astimezone(UTC)

        body: dict[str, Any] = {
            "start": start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "attendee": {
                "name": attendee_name,
                "email": attendee_email,
                "timeZone": timezone,
            },
        }
        if config.event_type_id is not None:
            body["eventTypeId"] = config.event_type_id
        else:
            body["eventTypeSlug"] = config.event_type_slug
            body["username"] = config.username
        if config.organization_slug:
            body["organizationSlug"] = config.organization_slug
        if notes.strip():
            body["bookingFieldsResponses"] = {"notes": notes.strip()}

        payload = await self._request(
            "POST",
            "/v2/bookings",
            json=body,
            api_versions=CALCOM_API_VERSIONS,
        )
        data = payload.get("data", payload)
        booking_uid = data.get("uid") or data.get("id")
        if booking_uid is None:
            raise CalComError("Cal.com booking response did not include a booking id.")

        meeting_url = (
            data.get("meetingUrl")
            or data.get("location")
            or data.get("videoCallUrl")
        )
        start_value = data.get("start") or body["start"]
        parsed_start = datetime.fromisoformat(start_value.replace("Z", "+00:00"))
        logger.info("created Cal.com booking %s for %s", booking_uid, attendee_email)
        return CalComBookingResult(
            booking_uid=str(booking_uid),
            start_utc=parsed_start.astimezone(UTC),
            meeting_url=meeting_url,
        )
