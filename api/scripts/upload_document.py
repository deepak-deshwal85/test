"""Upload a document to a Qdrant collection via the RAG API."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _headers() -> dict[str, str]:
    headers: dict[str, str] = {}
    api_key = os.getenv("RAG_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def upload_document(
    *,
    file_path: Path,
    collection: str,
    base_url: str,
) -> dict:
    url = f"{base_url.rstrip('/')}/v1/collections/{collection}/documents"
    with file_path.open("rb") as handle:
        response = httpx.post(
            url,
            files={"file": (file_path.name, handle)},
            headers=_headers(),
            timeout=120.0,
        )
    response.raise_for_status()
    return response.json()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path, help="PDF, TXT, or MD file to upload")
    parser.add_argument(
        "--collection",
        help="Qdrant collection name (client email id, e.g. client@example.com)",
    )
    parser.add_argument(
        "--email",
        help="Client email id; used as the collection name",
    )
    parser.add_argument(
        "--phone",
        help="Legacy: phone digits; resolves to phone_{digits} collection",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("RAG_API_BASE_URL", "http://127.0.0.1:8090"),
        help="RAG API base URL",
    )
    args = parser.parse_args(argv)

    load_dotenv(_PROJECT_ROOT / ".env.local")
    load_dotenv(_PROJECT_ROOT / ".env")

    if not args.file.is_file():
        print(f"File not found: {args.file}", file=sys.stderr)
        return 1

    collection = args.collection
    if not collection and args.email:
        collection = args.email.strip().lower()
    if not collection and args.phone:
        digits = "".join(character for character in args.phone if character.isdigit())
        if not digits:
            print("Invalid --phone value", file=sys.stderr)
            return 1
        collection = f"phone_{digits}"
    if not collection:
        print("Provide --collection, --email, or --phone", file=sys.stderr)
        return 1

    result = upload_document(
        file_path=args.file,
        collection=collection,
        base_url=args.base_url,
    )
    print(
        f"Uploaded {result['source_uri']} to {result['collection']}: "
        f"{result['chunks_indexed']} chunks (document_id={result['document_id']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
