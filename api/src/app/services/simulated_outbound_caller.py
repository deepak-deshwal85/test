from __future__ import annotations

import logging

from app.domain.customer_models import CallAttemptResult, Customer

logger = logging.getLogger("telephone-rag-api")


class SimulatedOutboundCaller:
    async def place_call(
        self,
        *,
        customer: Customer,
        job_id,
    ) -> CallAttemptResult:
        detail = (
            f"SIMULATED call from client {customer.client_phone_number} "
            f"({customer.client_name}) to consumer {customer.consumer_phone_number}. "
            "Configure LiveKit SIP env vars for real dialing."
        )
        logger.warning(detail)
        return CallAttemptResult(
            customer_id=customer.id,
            consumer_phone_number=customer.consumer_phone_number,
            success=True,
            detail=detail,
        )
