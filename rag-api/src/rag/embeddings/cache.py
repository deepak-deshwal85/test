from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path

from rag.embeddings.base import EmbeddingConfig


def normalize_cache_text(text: str) -> str:
    lowered = " ".join(text.strip().lower().split())
    return re.sub(r"[^\w\s]", "", lowered).strip()


def embedding_cache_key(config: EmbeddingConfig, text: str) -> str:
    normalized = normalize_cache_text(text)
    fingerprint = f"{config.provider}:{config.model}:{config.dimensions}:{normalized}"
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()


class EmbeddingCache:
    """Persistent SQLite cache for text embeddings (queries and document chunks)."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                cache_key TEXT PRIMARY KEY,
                vector_json TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def get(self, config: EmbeddingConfig, text: str) -> list[float] | None:
        key = embedding_cache_key(config, text)
        row = self._conn.execute(
            "SELECT vector_json FROM embeddings WHERE cache_key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        return [float(value) for value in json.loads(row[0])]

    def put(self, config: EmbeddingConfig, text: str, vector: list[float]) -> None:
        key = embedding_cache_key(config, text)
        self._conn.execute(
            """
            INSERT INTO embeddings (cache_key, vector_json, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                vector_json = excluded.vector_json,
                created_at = excluded.created_at
            """,
            (key, json.dumps(vector), time.time()),
        )
        self._conn.commit()
