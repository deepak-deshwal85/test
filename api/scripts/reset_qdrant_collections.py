"""Delete all Qdrant collections and optionally upload a document."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from app.core.config import get_settings  # noqa: E402
from app.db.qdrant_repository import QdrantRepository  # noqa: E402

load_dotenv(_PROJECT_ROOT / ".env.local")
load_dotenv(_PROJECT_ROOT / ".env")


def delete_all_collections() -> list[str]:
    settings = get_settings()
    repository = QdrantRepository(settings)
    deleted: list[str] = []
    for collection in repository.list_collections():
        repository.delete_collection(collection)
        deleted.append(collection)
        print(f"Deleted collection {collection}")
    if not deleted:
        print("No collections to delete.")
    return deleted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--upload",
        type=Path,
        help="After reset, upload this file via upload_document.py",
    )
    parser.add_argument(
        "--phone",
        help="Phone digits for upload collection (phone_{digits})",
    )
    args = parser.parse_args(argv)

    delete_all_collections()

    if args.upload:
        if not args.phone:
            print("--phone is required with --upload", file=sys.stderr)
            return 1
        from upload_document import main as upload_main

        return upload_main(
            [
                str(args.upload),
                "--phone",
                args.phone,
            ]
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
