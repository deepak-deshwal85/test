from __future__ import annotations

import hashlib
import os

import httpx

from rag.embeddings.base import EmbeddingConfig

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
            raise ValueError(
                "OPENAI_API_KEY is required for OpenAI embeddings when using the RAG service."
            )
        self._base_url = (
            base_url or os.getenv("OPENAI_BASE_URL", DEFAULT_OPENAI_BASE_URL)
        ).rstrip("/")
        self._http_client = http_client
        self._owns_client = http_client is None

    @property
    def config(self) -> EmbeddingConfig:
        return self._config

    def model_hash(self) -> str:
        fingerprint = (
            f"{self._config.provider}:{self._config.model}:{self._config.dimensions}"
        )
        return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()

    def _client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=60.0)
            self._owns_client = True
        return self._http_client

    def close(self) -> None:
        if self._owns_client and self._http_client is not None:
            self._http_client.close()
            self._http_client = None

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
        embeddings: list[list[float]] = []
        for item in ordered:
            vector = [float(value) for value in item["embedding"]]
            if len(vector) != self._config.dimensions:
                raise ValueError(
                    f"Embedding dimension mismatch: expected {self._config.dimensions}, "
                    f"got {len(vector)}"
                )
            embeddings.append(vector)
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]
