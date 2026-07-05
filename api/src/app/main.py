from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.dependencies import (
    get_embedding_provider_factory,
    get_qdrant_repository,
    reset_rag_clients,
)
from app.core.logging import configure_logging
from app.db.postgres.session import dispose_engine, init_engine
from app.routers import (
    call_jobs,
    collections,
    customers,
    documents,
    embeddings,
    health,
    search,
)

logger = logging.getLogger("telephone-rag-api")

configure_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    init_engine(settings)
    logger.info("database engine initialized")
    get_qdrant_repository(settings)
    logger.info("qdrant client warmed")
    get_embedding_provider_factory(settings).get_provider()
    logger.info("embedding provider warmed")
    yield
    await dispose_engine()
    reset_rag_clients()
    logger.info("database engine disposed")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "RAG REST API with Qdrant vector storage, customer management, "
            "and outbound call jobs."
        ),
        lifespan=lifespan,
    )

    app.include_router(health.router)
    app.include_router(embeddings.router)
    app.include_router(collections.router)
    app.include_router(documents.router)
    app.include_router(search.router)
    app.include_router(customers.router)
    app.include_router(call_jobs.router)

    return app


app = create_app()
