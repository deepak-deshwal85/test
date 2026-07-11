from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.dependencies import (
    get_embedding_provider_factory,
    get_qdrant_repository,
    reset_rag_clients,
)
from app.core.logging import configure_logging
from app.db.postgres.session import (
    dispose_engine,
    init_engine,
)
from app.routers import (
    call_jobs,
    call_summaries,
    clients,
    collections,
    customers,
    documents,
    embeddings,
    health,
    search,
    voice_agent_config,
)

logger = logging.getLogger("relaydesk-api")

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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(embeddings.router)
    app.include_router(collections.router)
    app.include_router(documents.router)
    app.include_router(search.router)
    app.include_router(customers.router)
    app.include_router(call_summaries.router)
    app.include_router(voice_agent_config.router)
    app.include_router(clients.router)
    app.include_router(call_jobs.router)

    return app


app = create_app()
