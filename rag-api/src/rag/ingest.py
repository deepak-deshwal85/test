from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True)
class SourceDocument:
    source_uri: str
    text: str


def chunk_text(
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


def load_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_pdf_file(path: Path) -> str:
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def load_documents(source_path: Path) -> list[SourceDocument]:
    if source_path.is_file():
        paths = [source_path]
    elif source_path.is_dir():
        paths = sorted(
            path
            for path in source_path.rglob("*")
            if path.is_file() and path.suffix.lower() in {".txt", ".md", ".pdf"}
        )
    else:
        raise FileNotFoundError(f"Source path does not exist: {source_path}")

    documents: list[SourceDocument] = []
    for path in paths:
        suffix = path.suffix.lower()
        text = load_pdf_file(path) if suffix == ".pdf" else load_text_file(path)
        if text.strip():
            documents.append(SourceDocument(source_uri=path.name, text=text))
    return documents
