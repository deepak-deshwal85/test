"""Shared helpers for api/scripts/init_db.py and reset_db.py."""

from __future__ import annotations

import os
import re
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

SCRIPTS_DIR = Path(__file__).resolve().parent
DB_DIR = SCRIPTS_DIR / "db"
PROJECT_ROOT = SCRIPTS_DIR.parent


def load_env() -> None:
    load_dotenv(PROJECT_ROOT / ".env.local")
    load_dotenv(PROJECT_ROOT / ".env")


def resolve_database_url(explicit: str | None = None) -> str:
    database_url = (explicit or os.getenv("DATABASE_URL", "")).strip()
    if not database_url:
        raise ValueError(
            "DATABASE_URL is required. Set it in api/.env or the environment."
        )
    if not re.match(r"^postgresql(\+asyncpg)?://", database_url):
        raise ValueError(
            "DATABASE_URL must be a PostgreSQL URL "
            "(postgresql+asyncpg://user:pass@host:port/db)."
        )
    return database_url


def to_asyncpg_dsn(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return database_url


def split_sql_statements(sql_text: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
    if buffer:
        trailing = "\n".join(buffer).strip()
        if trailing:
            statements.append(trailing)
    return statements


async def run_sql_file(connection: asyncpg.Connection, path: Path) -> int:
    sql_text = path.read_text(encoding="utf-8")
    statements = split_sql_statements(sql_text)
    for statement in statements:
        await connection.execute(statement)
    return len(statements)


async def drop_schema(connection: asyncpg.Connection) -> int:
    path = DB_DIR / "drop.sql"
    count = await run_sql_file(connection, path)
    print(f"Dropped tables ({count} statements) from {path.name}")
    return count


async def apply_schema(connection: asyncpg.Connection) -> int:
    path = DB_DIR / "schema.sql"
    count = await run_sql_file(connection, path)
    print(f"Applied schema ({count} statements) from {path.name}")
    return count


async def apply_seed(connection: asyncpg.Connection) -> int:
    path = DB_DIR / "seed.sql"
    count = await run_sql_file(connection, path)
    print(f"Applied seed data ({count} statements) from {path.name}")
    return count
