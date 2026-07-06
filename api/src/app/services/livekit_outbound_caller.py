from __future__ import annotations

import json
import logging
from uuid import UUID

from livekit import api

from app.core.config import Settings
from app.domain.customer_models import CallAttemptResult, Customer, format_sip_phone

logger = logging.getLogger("relaydesk-api")


class LiveKitOutboundCaller:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def place_call(
        self,
        *,
        customer: Customer,
        job_id: UUID,
    ) -> CallAttemptResult:
        room_name = f"outbound-{job_id}-{customer.id}"
        consumer_phone = format_sip_phone(customer.consumer_phone_number)
        metadata = json.dumps(
            {
                "call_type": "outbound",
                "client_phone_number": customer.client_phone_number,
                "client_name": customer.client_name,
                "consumer_phone_number": customer.consumer_phone_number,
                "customer_id": customer.id,
                "job_id": str(job_id),
            }
        )

        logger.info(
            "dialing consumer job_id=%s client=%s (%s) consumer=%s room=%s",
            job_id,
            customer.client_phone_number,
            customer.client_name,
            consumer_phone,
            room_name,
        )

        try:
            async with api.LiveKitAPI(
                self._settings.livekit_url,
                self._settings.livekit_api_key,
                self._settings.livekit_api_secret,
            ) as lk:
                await lk.agent_dispatch.create_dispatch(
                    api.CreateAgentDispatchRequest(
                        agent_name=self._settings.livekit_agent_name,
                        room=room_name,
                        metadata=metadata,
                    )
                )
                logger.info(
                    "agent dispatch created room=%s agent=%s",
                    room_name,
                    self._settings.livekit_agent_name,
                )

                await lk.sip.create_sip_participant(
                    api.CreateSIPParticipantRequest(
                        room_name=room_name,
                        sip_trunk_id=self._settings.livekit_sip_outbound_trunk_id,
                        sip_call_to=consumer_phone,
                        participant_identity=f"consumer-{customer.id}",
                        participant_name=customer.client_name,
                        wait_until_answered=False,
                    )
                )

            detail = (
                f"LiveKit outbound call initiated from client "
                f"{customer.client_phone_number} to {consumer_phone} in room {room_name}"
            )
            logger.info(detail)
            return CallAttemptResult(
                customer_id=customer.id,
                consumer_phone_number=customer.consumer_phone_number,
                success=True,
                detail=detail,
            )
        except Exception as exc:
            logger.exception(
                "livekit outbound call failed job_id=%s customer_id=%s",
                job_id,
                customer.id,
            )
            return CallAttemptResult(
                customer_id=customer.id,
                consumer_phone_number=customer.consumer_phone_number,
                success=False,
                detail=str(exc),
            )
