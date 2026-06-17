import json
import logging
import math
from dataclasses import dataclass
from typing import Callable

from client_config import ClientConfig
from paths import EMBEDDINGS_DIR

logger = logging.getLogger("agent-telephone-agent")

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_TOP_K = 3


@dataclass(frozen=True)
class RagChunk:
    text: str
    embedding: list[float]


@dataclass(frozen=True)
class RagStore:
    model_name: str
    chunks: list[RagChunk]
    embed_query: Callable[[str], list[float]]

    def retrieve(self, query_text: str, top_k: int = DEFAULT_TOP_K) -> list[str]:
        if not self.chunks:
            return []

        query_embedding = self.embed_query(query_text)
        scored = [
            (_cosine_similarity(query_embedding, chunk.embedding), chunk.text)
            for chunk in self.chunks
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [text for _, text in scored[:top_k]]

    def answer(self, query_text: str, top_k: int = DEFAULT_TOP_K) -> str:
        matches = self.retrieve(query_text, top_k=top_k)
        if not matches:
            return "I could not find relevant information in the knowledge base for that question."

        context = "\n\n".join(matches)
        return (
            "Use the following knowledge base excerpts to answer the caller. "
            "If the excerpts do not contain the answer, say you do not have that information.\n\n"
            f"{context}"
        )


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0

    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _default_embed_query(model_name: str) -> Callable[[str], list[float]]:
    from fastembed import TextEmbedding

    model = TextEmbedding(model_name=model_name)

    def embed_query(text: str) -> list[float]:
        return [float(value) for value in next(model.embed([text]))]

    return embed_query


def load_rag_store(
    client_config: ClientConfig,
    embed_query: Callable[[str], list[float]] | None = None,
) -> RagStore:
    embeddings_path = client_config.embeddings_path
    if not embeddings_path.is_file():
        raise FileNotFoundError(
            f"Embeddings file not found for phone {client_config.phone_number}: "
            f"{embeddings_path}"
        )

    with embeddings_path.open(encoding="utf-8") as f:
        data = json.load(f)

    model_name = data.get("model", DEFAULT_EMBEDDING_MODEL)
    chunks = [
        RagChunk(text=item["text"], embedding=item["embedding"])
        for item in data.get("chunks", [])
    ]

    return RagStore(
        model_name=model_name,
        chunks=chunks,
        embed_query=embed_query or _default_embed_query(model_name),
    )


def load_rag_store_from_embeddings_file(
    embeddings_file: str,
    embed_query: Callable[[str], list[float]] | None = None,
) -> RagStore:
    path = EMBEDDINGS_DIR / embeddings_file
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    model_name = data.get("model", DEFAULT_EMBEDDING_MODEL)
    chunks = [
        RagChunk(text=item["text"], embedding=item["embedding"])
        for item in data.get("chunks", [])
    ]
    return RagStore(
        model_name=model_name,
        chunks=chunks,
        embed_query=embed_query or _default_embed_query(model_name),
    )
