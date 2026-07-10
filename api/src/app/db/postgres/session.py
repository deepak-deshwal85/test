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
                CREATE TABLE IF NOT EXISTS clients (
                    id SERIAL PRIMARY KEY,
                    client_phone_number VARCHAR(32),
                    client_business_phone_number VARCHAR(32) UNIQUE,
                    client_name VARCHAR(255) NOT NULL DEFAULT '',
                    client_email_id VARCHAR(255) NOT NULL UNIQUE,
                    cognito_sub VARCHAR(255) UNIQUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        await connection.execute(
            text(
                """
                ALTER TABLE IF EXISTS clients
                ADD COLUMN IF NOT EXISTS client_business_phone_number VARCHAR(32) UNIQUE
                """
            )
        )
        await connection.execute(
            text(
                """
                UPDATE clients
                SET client_business_phone_number = client_phone_number
                WHERE client_business_phone_number IS NULL
                  AND client_phone_number IS NOT NULL
                """
            )
        )
        await connection.execute(
            text(
                """
                ALTER TABLE IF EXISTS clients
                ALTER COLUMN client_phone_number DROP NOT NULL
                """
            )
        )
        await connection.execute(
            text(
                """
                ALTER TABLE IF EXISTS customers
                ADD COLUMN IF NOT EXISTS client_business_phone_number VARCHAR(32)
                """
            )
        )
        await connection.execute(
            text(
                """
                UPDATE customers
                SET client_business_phone_number = client_phone_number
                WHERE client_business_phone_number IS NULL
                  AND client_phone_number IS NOT NULL
                """
            )
        )
        await connection.execute(
            text(
                """
                ALTER TABLE IF EXISTS call_jobs
                ADD COLUMN IF NOT EXISTS client_business_phone_number VARCHAR(32)
                """
            )
        )
        await connection.execute(
            text(
                """
                UPDATE call_jobs
                SET client_business_phone_number = client_phone_number
                WHERE client_business_phone_number IS NULL
                  AND client_phone_number IS NOT NULL
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_customers_client_business_phone
                ON customers (client_business_phone_number)
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_call_jobs_client_business_phone
                ON call_jobs (client_business_phone_number)
                """
            )
        )
        await connection.execute(
            text(
                """
                ALTER TABLE IF EXISTS clients
                ADD COLUMN IF NOT EXISTS client_name VARCHAR(255) NOT NULL DEFAULT ''
                """
            )
        )
        await connection.execute(
            text(
                """
                ALTER TABLE IF EXISTS clients
                ADD COLUMN IF NOT EXISTS cognito_sub VARCHAR(255) UNIQUE
                """
            )
        )
        await connection.execute(
            text(
                """
                ALTER TABLE IF EXISTS customers
                ADD COLUMN IF NOT EXISTS client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL
                """
            )
        )
        await connection.execute(
            text(
                """
                ALTER TABLE IF EXISTS customers
                ADD COLUMN IF NOT EXISTS client_email_id VARCHAR(255) NOT NULL DEFAULT 'unknown@example.com'
                """
            )
        )
        await connection.execute(
            text(
                """
                ALTER TABLE IF EXISTS customers
                ADD COLUMN IF NOT EXISTS consumer_email_id VARCHAR(255) NOT NULL DEFAULT 'unknown@example.com'
                """
            )
        )
        await connection.execute(
            text(
                """
                ALTER TABLE IF EXISTS customers
                ADD COLUMN IF NOT EXISTS is_approved BOOLEAN NOT NULL DEFAULT FALSE
                """
            )
        )
        await connection.execute(
            text(
                """
                ALTER TABLE IF EXISTS call_jobs
                ADD COLUMN IF NOT EXISTS client_email_id VARCHAR(255) NOT NULL DEFAULT 'unknown@example.com'
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_customers_client_email
                ON customers (client_email_id)
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_call_jobs_client_email
                ON call_jobs (client_email_id)
                """
            )
        )
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
                ALTER TABLE IF EXISTS customers
                ALTER COLUMN client_phone_number DROP NOT NULL
                """
            )
        )
        await connection.execute(
            text(
                """
                UPDATE customers
                SET client_phone_number = client_business_phone_number
                WHERE client_phone_number IS NULL
                  AND client_business_phone_number IS NOT NULL
                """
            )
        )
        await connection.execute(
            text(
                """
                UPDATE customers AS c
                SET client_email_id = cl.client_email_id
                FROM clients AS cl
                WHERE c.client_business_phone_number = cl.client_business_phone_number
                  AND cl.client_email_id IS NOT NULL
                  AND (
                    c.client_email_id IS NULL
                    OR c.client_email_id = 'unknown@example.com'
                  )
                """
            )
        )
        await connection.execute(
            text(
                """
                ALTER TABLE customers
                DROP CONSTRAINT IF EXISTS uq_customers_client_consumer
                """
            )
        )
        await connection.execute(
            text("DROP INDEX IF EXISTS uq_customers_client_consumer")
        )
        await connection.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_customers_client_consumer
                ON customers (client_email_id, consumer_phone_number)
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
