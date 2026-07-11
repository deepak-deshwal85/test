from __future__ import annotations

import logging
import time

import httpx

from rag_client.config import RagClientSettings, resolve_rag_api_url
from rag_client.models import RagSearchHit
from rag_client.oauth_token import get_cognito_token_provider

logger = logging.getLogger("relaydesk-agent")


class ApiRagRetriever:
    """Calls the standalone RAG REST API."""

    def __init__(
        self,
        *,
        base_url: str,
        client_email_id: str,
        settings: RagClientSettings,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client_email_id = client_email_id.strip().lower()
        self._settings = settings
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

    async def warmup(self) -> None:
        try:
            await self._client().get("/health")
        except Exception:
            logger.debug("rag api warmup failed", exc_info=True)

    async def search(self, query: str, *, max_results: int) -> list[RagSearchHit]:
        payload = {
            "client_email_id": self._client_email_id,
            "query": query,
            "max_results": max_results,
        }
        started = time.perf_counter()
        headers = await self._headers()
        if self._token_provider is not None and "Authorization" not in headers:
            raise RuntimeError("Cognito token provider is configured but no bearer token was produced")

        response = await self._client().post(
            "/v1/search",
            json=payload,
            headers=headers,
        )
        if response.status_code == 401:
            logger.error(
                "rag api unauthorized client_email_id=%s detail=%s auth_configured=%s",
                self._client_email_id,
                response.text[:300],
                self._token_provider is not None,
            )
        response.raise_for_status()
        data = response.json()
        hits = self._parse_hits(data)
        logger.info(
            "rag api search client_email_id=%s hits=%d api_ms=%.0f",
            self._client_email_id,
            len(hits),
            (time.perf_counter() - started) * 1000,
        )
        return hits

    @staticmethod
    def _parse_hits(data: dict[str, object]) -> list[RagSearchHit]:
        raw_hits = data.get("hits", [])
        if not isinstance(raw_hits, list):
            raise RuntimeError("RAG API returned an unexpected search payload")

        results: list[RagSearchHit] = []
        for hit in raw_hits:
            if not isinstance(hit, dict):
                continue
            text = str(hit.get("text") or "")
            if not text:
                continue
            results.append(
                RagSearchHit(
                    text=text,
                    score=float(hit.get("score", 0.0)),
                    source_uri=str(hit.get("source_uri") or "") or None,
                )
            )
        return results


def create_api_rag_retriever(
    *,
    client_config,
    settings: RagClientSettings,
) -> ApiRagRetriever:
    if not client_config.client_email_id:
        raise ValueError(
            f"client_email_id is required for RAG API search (phone {client_config.phone_number})"
        )
    return ApiRagRetriever(
        base_url=resolve_rag_api_url(client_config, settings),
        client_email_id=client_config.client_email_id,
        settings=settings,
    )
