#!/usr/bin/env python3
"""Upload a resume document to the RAG API / Qdrant collection."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from client_config import load_client_config, resolve_client_config
from rag.config import load_rag_settings, resolve_qdrant_collection


def main() -> int:
    load_dotenv(".env.local")
    load_dotenv(".env")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phone",
        default=os.getenv("CLIENT_PHONE_OVERRIDE", "911171366880"),
        help="Phone number whose Qdrant collection should receive the document",
    )
    parser.add_argument(
        "--file",
        type=Path,
        required=True,
        help="PDF/TXT/MD file to upload",
    )
    parser.add_argument(
        "--collection",
        help="Override Qdrant collection name",
    )
    args = parser.parse_args()

    if not args.file.is_file():
        print(f"File not found: {args.file}")
        return 1

    phone_digits = "".join(character for character in args.phone if character.isdigit())
    client_config = resolve_client_config(phone_digits) or load_client_config(
        phone_digits
    )
    settings = load_rag_settings()
    collection = args.collection or resolve_qdrant_collection(client_config, settings)
    base_url = settings.rag_api_base_url.rstrip("/")

    headers: dict[str, str] = {}
    api_key = os.getenv("RAG_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    with args.file.open("rb") as handle:
        response = httpx.post(
            f"{base_url}/v1/collections/{collection}/documents",
            files={"file": (args.file.name, handle, "application/octet-stream")},
            headers=headers,
            timeout=120.0,
        )
    response.raise_for_status()
    print(response.json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
