from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from pypdf import PdfReader

from app.core.config import Settings
from app.db.qdrant_repository import QdrantRepository, new_document_id, new_point_id
from app.domain.models import DocumentSummary, IndexedChunk, IngestResult
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger("telephone-rag-api")

SUPPORTED_SUFFIXES = {".txt", ".md", ".pdf"}


@dataclass(frozen=True)
class _ParsedDocument:
    source_uri: str
    text: str


class DocumentService:
    def __init__(
        self,
        settings: Settings,
        qdrant: QdrantRepository,
        embedding_service: EmbeddingService,
    ) -> None:
        self._settings = settings
        self._qdrant = qdrant
        self._embedding_service = embedding_service

    @staticmethod
    def _chunk_text(
        text: str,
        *,
        max_chars: int = 800,
        overlap: int = 100,
    ) -> list[str]:
        if max_chars <= 0:
            raise ValueError("max_chars must be > 0")
        if overlap < 0 or overlap >= max_chars:
            raise ValueError("overlap must be >= 0 and < max_chars")

        normalized = " ".join(text.split())
        if not normalized:
            return []

        chunks: list[str] = []
        start = 0
        while start < len(normalized):
            end = min(start + max_chars, len(normalized))
            chunks.append(normalized[start:end])
            if end == len(normalized):
                break
            start = end - overlap
        return chunks

    @staticmethod
    def _read_text_file(path: Path) -> str:
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _read_pdf_file(path: Path) -> str:
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)

    @classmethod
    def _parse_uploaded_file(cls, path: Path, *, source_uri: str) -> _ParsedDocument:
        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_SUFFIXES:
            raise ValueError(
                f"Unsupported file type {suffix!r}. Use one of: {', '.join(sorted(SUPPORTED_SUFFIXES))}"
            )

        text = (
            cls._read_pdf_file(path) if suffix == ".pdf" else cls._read_text_file(path)
        )
        if not text.strip():
            raise ValueError(f"No extractable text in {source_uri!r}")

        return _ParsedDocument(source_uri=source_uri, text=text)

    def ingest_upload(
        self,
        *,
        collection: str,
        filename: str,
        content: bytes,
        max_chars: int = 800,
        overlap: int = 100,
    ) -> IngestResult:
        if not content:
            raise ValueError("Uploaded file is empty")

        started = time.perf_counter()
        suffix = Path(filename).suffix.lower() or ".txt"
        with NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            handle.write(content)
            temp_path = Path(handle.name)

        try:
            document = self._parse_uploaded_file(temp_path, source_uri=filename)
        finally:
            temp_path.unlink(missing_ok=True)

        chunks = self._chunk_text(document.text, max_chars=max_chars, overlap=overlap)
        if not chunks:
            raise ValueError(f"No text chunks produced from {filename!r}")

        embedding_result = self._embedding_service.create_embeddings(chunks)
        self._qdrant.ensure_collection(
            collection,
            vector_size=self._settings.embedder_dimensions,
        )

        document_id = new_document_id()
        indexed_chunks = [
            IndexedChunk(
                point_id=new_point_id(),
                text=chunk,
                source_uri=document.source_uri,
                document_id=document_id,
                chunk_index=index,
            )
            for index, chunk in enumerate(chunks)
        ]
        count = self._qdrant.upsert_chunks(
            collection,
            chunks=indexed_chunks,
            embeddings=embedding_result.embeddings,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "ingest complete collection=%s file=%r chunks=%d "
            "embed_cache_hits=%d embed_cache_misses=%d total_ms=%.0f",
            collection,
            filename,
            count,
            embedding_result.cache_hits,
            embedding_result.cache_misses,
            elapsed_ms,
        )
        return IngestResult(
            collection=collection,
            document_id=document_id,
            source_uri=document.source_uri,
            chunks_indexed=count,
        )

    def list_documents(self, collection: str) -> list[DocumentSummary]:
        return self._qdrant.list_documents(collection)

    def delete_document(self, collection: str, document_id: str) -> None:
        self._qdrant.delete_document(collection, document_id)
