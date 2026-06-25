from __future__ import annotations

import logging

import httpx

from app.core.config import Settings
from app.domain.customer_models import CallAttemptResult, Customer

logger = logging.getLogger("telephone-rag-api")


class OutboundCaller:
    """Places outbound calls to consumers. Wire to LiveKit/SIP via webhook when ready."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def place_call(
        self,
        *,
        customer: Customer,
    ) -> CallAttemptResult:
        payload = {
            "client_phone_number": customer.client_phone_number,
            "client_name": customer.client_name,
            "consumer_phone_number": customer.consumer_phone_number,
            "customer_id": customer.id,
        }

        webhook_url = self._settings.outbound_call_webhook_url
        if webhook_url:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(webhook_url, json=payload)
                    response.raise_for_status()
                detail = f"Webhook accepted call to {customer.consumer_phone_number}"
                logger.info(
                    "outbound call webhook client=%s consumer=%s",
                    customer.client_phone_number,
                    customer.consumer_phone_number,
                )
                return CallAttemptResult(
                    customer_id=customer.id,
                    consumer_phone_number=customer.consumer_phone_number,
                    success=True,
                    detail=detail,
                )
            except Exception as exc:
                logger.exception(
                    "outbound call webhook failed customer_id=%s", customer.id
                )
                return CallAttemptResult(
                    customer_id=customer.id,
                    consumer_phone_number=customer.consumer_phone_number,
                    success=False,
                    detail=str(exc),
                )

        logger.info(
            "simulated outbound call client=%s (%s) -> consumer=%s",
            customer.client_phone_number,
            customer.client_name,
            customer.consumer_phone_number,
        )
        return CallAttemptResult(
            customer_id=customer.id,
            consumer_phone_number=customer.consumer_phone_number,
            success=True,
            detail="Simulated call (set OUTBOUND_CALL_WEBHOOK_URL to dial via telephony)",
        )
