from __future__ import annotations

import asyncio
import logging

from app.services.voice_agent_schedule_service import VoiceAgentScheduleService

logger = logging.getLogger("relaydesk-api")

POLL_INTERVAL_SECONDS = 60


async def run_voice_agent_schedule_poller(
    service: VoiceAgentScheduleService,
    *,
    enabled: bool = True,
) -> None:
    if not enabled:
        logger.info("voice agent schedule poller disabled")
        return

    logger.info(
        "voice agent schedule poller started interval_seconds=%d",
        POLL_INTERVAL_SECONDS,
    )
    while True:
        try:
            job_ids = await service.execute_due(run_jobs=True)
            if job_ids:
                logger.info(
                    "voice agent schedule poller triggered jobs count=%d",
                    len(job_ids),
                )
        except Exception:
            logger.exception("voice agent schedule poller iteration failed")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
