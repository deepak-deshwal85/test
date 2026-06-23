from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str
    model: str
    dimensions: int


class EmbeddingProvider(Protocol):
    @property
    def config(self) -> EmbeddingConfig: ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...
