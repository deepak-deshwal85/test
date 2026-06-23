from __future__ import annotations

import os

import httpx

from app.db.embeddings.base import EmbeddingConfig

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


class OpenAIEmbeddingProvider:
    def __init__(
        self,
        config: EmbeddingConfig,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._config = config
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "").strip()
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI embeddings.")
        self._base_url = (
            base_url or os.getenv("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL)
        ).rstrip("/")
        self._http_client = http_client
        self._owns_client = http_client is None

    @property
    def config(self) -> EmbeddingConfig:
        return self._config

    def _client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=60.0)
            self._owns_client = True
        return self._http_client

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        payload: dict[str, object] = {
            "model": self._config.model,
            "input": texts,
        }
        if self._config.dimensions:
            payload["dimensions"] = self._config.dimensions

        response = self._client().post(
            f"{self._base_url}/embeddings",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()["data"]
        ordered = sorted(data, key=lambda item: item["index"])
        return [[float(value) for value in item["embedding"]] for item in ordered]
