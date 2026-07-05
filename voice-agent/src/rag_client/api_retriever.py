from __future__ import annotations

import logging
import os
import time

import httpx

from rag_client.config import RagClientSettings, resolve_rag_api_url
from rag_client.models import RagSearchHit

logger = logging.getLogger("agent-telephone-agent")


class ApiRagRetriever:
    """Calls the standalone RAG REST API."""

    def __init__(
        self,
        *,
        base_url: str,
        phone_number: str,
        settings: RagClientSettings,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._phone_number = phone_number
        self._settings = settings
        self._http_client = http_client
        self._owns_client = http_client is None
        api_key = os.getenv("RAG_API_KEY", "").strip()
        self._auth_headers: dict[str, str] = (
            {"Authorization": f"Bearer {api_key}"} if api_key else {}
        )

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

    def _headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json", **self._auth_headers}

    async def warmup(self) -> None:
        try:
            await self._client().get("/health")
        except Exception:
            logger.debug("rag api warmup failed", exc_info=True)

    async def search(self, query: str, *, max_results: int) -> list[RagSearchHit]:
        payload = {
            "phone_number": self._phone_number,
            "query": query,
            "max_results": max_results,
        }
        started = time.perf_counter()
        response = await self._client().post(
            "/v1/search",
            json=payload,
            headers=self._headers(),
        )
        response.raise_for_status()
        data = response.json()
        hits = self._parse_hits(data)
        logger.info(
            "rag api search phone=%s hits=%d api_ms=%.0f",
            self._phone_number,
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
    return ApiRagRetriever(
        base_url=resolve_rag_api_url(client_config, settings),
        phone_number=client_config.phone_number,
        settings=settings,
    )
