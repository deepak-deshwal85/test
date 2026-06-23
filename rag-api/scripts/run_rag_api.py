#!/usr/bin/env python3
"""Run the standalone RAG REST API (Qdrant + embeddings + document ingest)."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import uvicorn

from rag.api_server import create_app

logging.basicConfig(level=logging.INFO)


def main() -> int:
    load_dotenv(".env.local")
    load_dotenv(".env")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.getenv("RAG_API_HOST", "127.0.0.1"))
    parser.add_argument(
        "--port", type=int, default=int(os.getenv("RAG_API_PORT", "8090"))
    )
    args = parser.parse_args()

    uvicorn.run(create_app(), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
