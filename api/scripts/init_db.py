#!/usr/bin/env python3
"""Create RelayDesk PostgreSQL tables and optionally load dummy seed data.

Schema is NOT applied during API container startup — run this script after RDS
(or local Postgres) is available.

Usage:
  cd api
  uv run python scripts/init_db.py
  uv run python scripts/init_db.py --schema-only
  uv run python scripts/init_db.py --seed-only
"""
from __future__ import annotations

import argparse
import asyncio
import sys

import asyncpg
from db_runner import (
    apply_schema,
    apply_seed,
    load_env,
    resolve_database_url,
    to_asyncpg_dsn,
)


async def _run(*, database_url: str, schema: bool, seed: bool) -> None:
    dsn = to_asyncpg_dsn(database_url)
    connection = await asyncpg.connect(dsn)
    try:
        if schema:
            await apply_schema(connection)
        if seed:
            await apply_seed(connection)
    finally:
        await connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Initialize RelayDesk PostgreSQL schema and optional seed data."
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="Create tables and indexes only (no dummy data).",
    )
    parser.add_argument(
        "--seed-only",
        action="store_true",
        help="Insert dummy data only (tables must already exist).",
    )
    args = parser.parse_args()

    if args.schema_only and args.seed_only:
        print("Use only one of --schema-only or --seed-only.", file=sys.stderr)
        return 1

    run_schema = not args.seed_only
    run_seed = not args.schema_only

    load_env()
    try:
        database_url = resolve_database_url()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        asyncio.run(
            _run(
                database_url=database_url,
                schema=run_schema,
                seed=run_seed,
            )
        )
    except Exception as exc:
        print(f"Database init failed: {exc}", file=sys.stderr)
        return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
