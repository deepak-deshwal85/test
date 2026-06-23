from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RagSearchHit:
    text: str
    score: float
    source_uri: str | None = None


class RagRetriever(Protocol):
    async def search(self, query: str, *, max_results: int) -> list[RagSearchHit]: ...


def format_search_hits(hits: list[RagSearchHit]) -> str:
    if not hits:
        return "No matching information was found in the knowledge base."

    lines = ["Relevant document excerpts:"]
    for index, hit in enumerate(hits, start=1):
        source = f" (source: {hit.source_uri})" if hit.source_uri else ""
        lines.append(f"{index}. {hit.text}{source}")
    return "\n".join(lines)
