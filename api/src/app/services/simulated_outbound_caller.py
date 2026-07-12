from __future__ import annotations

import logging

from app.domain.consumer_models import CallAttemptResult, Consumer

logger = logging.getLogger("relaydesk-api")


class SimulatedOutboundCaller:
    async def place_call(
        self,
        *,
        consumer: Consumer,
        job_id,
    ) -> CallAttemptResult:
        detail = (
            f"SIMULATED call from client {consumer.client_business_phone_number} "
            f"({consumer.client_name}) to consumer {consumer.consumer_phone_number}. "
            "Configure LiveKit SIP env vars for real dialing."
        )
        logger.warning(detail)
        return CallAttemptResult(
            consumer_id=consumer.id,
            consumer_phone_number=consumer.consumer_phone_number,
            success=True,
            detail=detail,
        )
