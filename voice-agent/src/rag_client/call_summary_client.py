from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

import httpx

from rag_client.config import RagClientSettings, resolve_rag_api_url
from rag_client.oauth_token import get_cognito_token_provider
from client_config import ClientConfig

logger = logging.getLogger("relaydesk-agent")

MAX_SUMMARY_LENGTH = 8000


class CallSummaryApiClient:
    """Posts call summaries to the RelayDesk API after each voice session."""

    def __init__(
        self,
        *,
        base_url: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._http_client = http_client
        self._owns_client = http_client is None
        self._token_provider = get_cognito_token_provider()

    def _client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(30.0, connect=5.0),
            )
            self._owns_client = True
        return self._http_client

    async def aclose(self) -> None:
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
        if self._token_provider is not None:
            await self._token_provider.aclose()

    async def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._token_provider is not None:
            token = await self._token_provider.get_access_token()
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def create_call_summary(
        self,
        *,
        customer_id: int,
        call_start_time: datetime,
        call_end_time: datetime | None,
        call_summary: str,
        job_id: UUID | None = None,
        meeting_scheduled: bool = False,
    ) -> None:
        payload: dict[str, object] = {
            "customer_id": customer_id,
            "call_start_time": call_start_time.isoformat(),
            "call_end_time": call_end_time.isoformat() if call_end_time else None,
            "call_summary": call_summary[:MAX_SUMMARY_LENGTH],
            "meeting_scheduled": meeting_scheduled,
        }
        if job_id is not None:
            payload["job_id"] = str(job_id)

        headers = await self._headers()
        response = await self._client().post(
            "/v1/call-summaries",
            json=payload,
            headers=headers,
        )
        if response.status_code >= 400:
            logger.error(
                "call summary api failed status=%s detail=%s customer_id=%s",
                response.status_code,
                response.text,
                customer_id,
            )
            response.raise_for_status()


def create_call_summary_client(
    client_config: ClientConfig,
    settings: RagClientSettings | None = None,
) -> CallSummaryApiClient:
    from rag_client.config import load_rag_settings

    rag_settings = settings or load_rag_settings()
    return CallSummaryApiClient(base_url=resolve_rag_api_url(client_config, rag_settings))


async def persist_call_summary(
    *,
    client: CallSummaryApiClient,
    customer_id: int | None,
    job_id: UUID | None,
    call_start_time: datetime,
    call_end_time: datetime,
    call_summary: str,
    meeting_scheduled: bool = False,
) -> None:
    if customer_id is None:
        logger.info("skipping call summary save: no customer_id in job metadata")
        return
    if not call_summary.strip():
        call_summary = "Call completed with no transcript captured."

    try:
        await client.create_call_summary(
            customer_id=customer_id,
            call_start_time=call_start_time,
            call_end_time=call_end_time,
            call_summary=call_summary,
            job_id=job_id,
            meeting_scheduled=meeting_scheduled,
        )
        logger.info(
            "saved call summary customer_id=%s meeting_scheduled=%s duration_seconds=%.1f",
            customer_id,
            meeting_scheduled,
            (call_end_time - call_start_time).total_seconds(),
        )
    except Exception:
        logger.exception("failed to save call summary customer_id=%s", customer_id)
