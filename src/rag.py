import json
import logging
import math
from dataclasses import dataclass
from typing import Callable

from client_config import ClientConfig
from paths import EMBEDDINGS_DIR

logger = logging.getLogger("agent-telephone-agent")

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_TOP_K = 5
MIN_SIMILARITY_SCORE = 0.35
BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

_shared_models: dict[str, Callable[[str], list[float]]] = {}
@dataclass(frozen=True)
class RagChunk:
    text: str
    embedding: list[float]


@dataclass(frozen=True)
class RagStore:
    model_name: str
    chunks: list[RagChunk]
    embed_query: Callable[[str], list[float]]

    def retrieve(self, query_text: str, top_k: int = DEFAULT_TOP_K) -> list[tuple[float, str]]:
        if not self.chunks:
            return []

        query_embedding = self.embed_query(query_text)
        scored = [
            (_cosine_similarity(query_embedding, chunk.embedding), chunk.text)
            for chunk in self.chunks
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[:top_k]

    def answer(self, query_text: str, top_k: int = DEFAULT_TOP_K) -> str:
        scored_matches = self.retrieve(query_text, top_k=top_k)
        matches = [
            (score, text) for score, text in scored_matches if score >= MIN_SIMILARITY_SCORE
        ]

        if matches:
            logger.info(
                "rag match for %r: top score=%.3f chunks=%d",
                query_text,
                matches[0][0],
                len(matches),
            )
            excerpts = "\n".join(f"- {text}" for _, text in matches)
            return f"Relevant information from the resume:\n{excerpts}"

        if scored_matches:
            logger.warning(
                "rag low confidence for %r: top score=%.3f (min=%.3f)",
                query_text,
                scored_matches[0][0],
                MIN_SIMILARITY_SCORE,
            )
            best_score, best_text = scored_matches[0]
            return (
                "The closest resume excerpt may be relevant:\n"
                f"- {best_text}\n"
                f"(confidence score: {best_score:.2f})"
            )

        logger.warning("rag found no chunks for query %r", query_text)
        return "No matching information was found in the resume for that question."


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0

    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _format_query_for_embedding(query_text: str, model_name: str) -> str:
    if "bge" in model_name.lower():
        return f"{BGE_QUERY_PREFIX}{query_text}"
    return query_text


def create_embed_query(model_name: str = DEFAULT_EMBEDDING_MODEL) -> Callable[[str], list[float]]:
    if model_name in _shared_models:
        return _shared_models[model_name]

    from fastembed import TextEmbedding

    model = TextEmbedding(model_name=model_name)

    def embed_query(text: str) -> list[float]:
        prepared = _format_query_for_embedding(text, model_name)
        return [float(value) for value in next(model.embed([prepared]))]

    _shared_models[model_name] = embed_query
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

    logger.info(
        "loaded %d rag chunks for %s from %s",
        len(chunks),
        client_config.client_name,
        embeddings_path.name,
    )

    return RagStore(
        model_name=model_name,
        chunks=chunks,
        embed_query=embed_query or create_embed_query(model_name),
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
        embed_query=embed_query or create_embed_query(model_name),
    )
