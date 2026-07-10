from __future__ import annotations

import os

import pytest

from app.core.config import get_settings


@pytest.fixture(scope="session", autouse=True)
def _test_cloud_env() -> None:
    """Unit tests do not run local Postgres or Docker Qdrant."""
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+asyncpg://relaydesk_admin:test@127.0.0.1:15432/relaydesk",
    )
    os.environ.setdefault(
        "QDRANT_CLUSTER_ENDPOINT",
        "https://test-cluster.eu-central-1-0.aws.cloud.qdrant.io",
    )
    os.environ.setdefault("QDRANT_API_KEY", "test-qdrant-api-key")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
