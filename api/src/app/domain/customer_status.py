from __future__ import annotations

CUSTOMER_STATUS_READY = "READY"
CUSTOMER_STATUS_MEETING_SCHEDULED = "MEETING_SCHEDULED"
CUSTOMER_STATUS_MEETING_NOT_SCHEDULED = "MEETING_NOT_SCHEDULED"

VALID_CUSTOMER_STATUSES = frozenset(
    {
        CUSTOMER_STATUS_READY,
        CUSTOMER_STATUS_MEETING_SCHEDULED,
        CUSTOMER_STATUS_MEETING_NOT_SCHEDULED,
    }
)

VALID_CALL_SCHEDULES = frozenset({"yes", "no"})


def customer_status_after_call(*, meeting_scheduled: bool) -> str:
    return (
        CUSTOMER_STATUS_MEETING_SCHEDULED
        if meeting_scheduled
        else CUSTOMER_STATUS_MEETING_NOT_SCHEDULED
    )
