"""Generate per-phone-number embedding files from knowledge base PDFs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from fastembed import TextEmbedding
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from client_config import load_client_config
from paths import CONFIG_DIR, EMBEDDINGS_DIR, KNOWLEDGE_BASE_DIR
from rag import DEFAULT_EMBEDDING_MODEL

CHUNK_SIZE = 400
CHUNK_OVERLAP = 80


def extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def chunk_text(
    text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start = max(end - overlap, start + 1)

    return chunks


def build_embeddings_for_config(
    phone_number: str,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> Path:
    client_config = load_client_config(phone_number)
    pdf_path = KNOWLEDGE_BASE_DIR / client_config.knowledge_base_doc
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Knowledge base PDF not found: {pdf_path}")

    text = extract_pdf_text(pdf_path)
    chunks = chunk_text(text)
    if not chunks:
        raise ValueError(f"No text extracted from {pdf_path}")

    model = TextEmbedding(model_name=model_name)
    embeddings = list(model.embed(chunks))

    payload = {
        "phone_number": client_config.phone_number,
        "client_name": client_config.client_name,
        "source_doc": client_config.knowledge_base_doc,
        "model": model_name,
        "chunks": [
            {"text": chunk, "embedding": [float(value) for value in vector]}
            for chunk, vector in zip(chunks, embeddings, strict=True)
        ],
    }

    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = EMBEDDINGS_DIR / client_config.embeddings_file
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f)

    return output_path


def discover_phone_numbers() -> list[str]:
    return sorted(
        path.stem.removeprefix("phone_number_")
        for path in CONFIG_DIR.glob("phone_number_*.json")
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate RAG embedding files per phone number."
    )
    parser.add_argument(
        "--phone-number",
        action="append",
        dest="phone_numbers",
        help="Phone number to process (repeatable). Defaults to all config files.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_EMBEDDING_MODEL,
        help=f"Embedding model name (default: {DEFAULT_EMBEDDING_MODEL})",
    )
    args = parser.parse_args()

    phone_numbers = args.phone_numbers or discover_phone_numbers()
    if not phone_numbers:
        raise SystemExit("No phone_number_*.json config files found.")

    for phone_number in phone_numbers:
        output_path = build_embeddings_for_config(phone_number, model_name=args.model)
        print(f"Wrote embeddings for {phone_number} -> {output_path}")


if __name__ == "__main__":
    main()
