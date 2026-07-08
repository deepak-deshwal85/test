from __future__ import annotations

import ssl
from collections.abc import AsyncGenerator
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings
from app.db.postgres.base import Base
from app.db.postgres import models as _models  # noqa: F401

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _engine_connect_args(database_url: str) -> dict:
    hostname = urlparse(database_url).hostname or ""
    if hostname in {"", "localhost", "127.0.0.1"}:
        return {}

    # AWS RDS PostgreSQL requires encrypted connections (pg_hba: no encryption).
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    return {"ssl": ssl_context}


def init_engine(settings: Settings) -> AsyncEngine:
    global _engine, _session_factory
    if _engine is None:
        try:
            _engine = create_async_engine(
                settings.database_url,
                echo=settings.database_echo,
                pool_pre_ping=True,
                connect_args=_engine_connect_args(settings.database_url),
            )
        except ArgumentError as exc:
            raise RuntimeError(
                "Invalid DATABASE_URL. Expected format: "
                "postgresql+asyncpg://user:password@host:5432/database"
            ) from exc
        _session_factory = async_sessionmaker(
            _engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _engine


async def bootstrap_database_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

        # Postgres-only compatibility fixes for existing databases.
        if connection.dialect.name != "postgresql":
            return

        await connection.execute(
            text(
                """
                ALTER TABLE IF EXISTS call_jobs
                ADD COLUMN IF NOT EXISTS results_json TEXT
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_customers_client_phone
                ON customers (client_phone_number)
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_customers_client_consumer
                ON customers (client_phone_number, consumer_phone_number)
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_call_jobs_client_phone
                ON call_jobs (client_phone_number)
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_call_jobs_status
                ON call_jobs (status)
                """
            )
        )


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Database engine is not initialized")
    return _session_factory


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session
