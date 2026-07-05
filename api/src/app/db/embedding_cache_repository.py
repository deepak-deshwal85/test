from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path

from app.db.embeddings.base import EmbeddingConfig


def normalize_cache_text(text: str) -> str:
    lowered = " ".join(text.strip().lower().split())
    return re.sub(r"[^\w\s]", "", lowered).strip()


def embedding_cache_key(config: EmbeddingConfig, text: str) -> str:
    normalized = normalize_cache_text(text)
    fingerprint = f"{config.provider}:{config.model}:{config.dimensions}:{normalized}"
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()


class EmbeddingCacheRepository:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                cache_key TEXT PRIMARY KEY,
                source_text TEXT NOT NULL,
                vector_json TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        self._conn.commit()

    def get(self, config: EmbeddingConfig, text: str) -> list[float] | None:
        key = embedding_cache_key(config, text)
        row = self._conn.execute(
            "SELECT vector_json FROM embeddings WHERE cache_key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        return [float(value) for value in json.loads(row[0])]

    def put(self, config: EmbeddingConfig, text: str, vector: list[float]) -> str:
        key = embedding_cache_key(config, text)
        self._conn.execute(
            """
            INSERT INTO embeddings (cache_key, source_text, vector_json, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                source_text = excluded.source_text,
                vector_json = excluded.vector_json,
                created_at = excluded.created_at
            """,
            (key, text, json.dumps(vector), time.time()),
        )
        self._conn.commit()
        return key

    def put_many(
        self,
        config: EmbeddingConfig,
        items: list[tuple[str, list[float]]],
    ) -> None:
        """Insert multiple embeddings in a single transaction."""
        if not items:
            return
        now = time.time()
        rows = [
            (embedding_cache_key(config, text), text, json.dumps(vector), now)
            for text, vector in items
        ]
        self._conn.executemany(
            """
            INSERT INTO embeddings (cache_key, source_text, vector_json, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                source_text = excluded.source_text,
                vector_json = excluded.vector_json,
                created_at = excluded.created_at
            """,
            rows,
        )
        self._conn.commit()

    def delete(self, config: EmbeddingConfig, text: str) -> bool:
        key = embedding_cache_key(config, text)
        cursor = self._conn.execute(
            "DELETE FROM embeddings WHERE cache_key = ?",
            (key,),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def clear(self) -> int:
        cursor = self._conn.execute("DELETE FROM embeddings")
        self._conn.commit()
        return cursor.rowcount

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()
        return int(row[0]) if row else 0
