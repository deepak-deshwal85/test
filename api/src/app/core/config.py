from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DATA_DIR = _PROJECT_ROOT / "data"

load_dotenv(_PROJECT_ROOT / ".env.local")
load_dotenv(_PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_PROJECT_ROOT / ".env.local", _PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Telephone Agent RAG API"
    app_version: str = "2.0.0"
    api_host: str = Field(default="127.0.0.1", alias="RAG_API_HOST")
    api_port: int = Field(default=8090, alias="RAG_API_PORT")

    rag_backend: str = Field(default="qdrant", alias="RAG_BACKEND")
    rag_max_results: int = Field(default=5, alias="RAG_MAX_RESULTS")

    embedder_provider: str = Field(default="openai", alias="RAG_EMBEDDER_PROVIDER")
    embedder_model: str = Field(
        default="text-embedding-3-small",
        alias="RAG_EMBEDDER_MODEL",
    )
    embedder_dimensions: int = Field(default=1536, alias="RAG_EMBEDDER_DIMENSIONS")
    embedder_cache_enabled: bool = Field(default=True, alias="RAG_EMBEDDER_CACHE")
    embedder_cache_path: Path = Field(
        default=_DATA_DIR / "embedding_cache.sqlite",
        alias="RAG_EMBEDDER_CACHE_PATH",
    )

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")

    qdrant_url: str = Field(default="http://127.0.0.1:6333", alias="QDRANT_URL")
    qdrant_api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")
    rag_api_key: str | None = Field(default=None, alias="RAG_API_KEY")

    database_url: str = Field(
        default="postgresql+asyncpg://postgres:1234@localhost:5432/telephone_agent",
        alias="DATABASE_URL",
    )
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    outbound_call_webhook_url: str | None = Field(
        default=None, alias="OUTBOUND_CALL_WEBHOOK_URL"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
