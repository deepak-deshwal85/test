from __future__ import annotations

import logging

from fastapi import FastAPI

from app.core.config import get_settings
from app.routers import collections, documents, embeddings, health, search

logger = logging.getLogger("telephone-rag-api")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="RAG REST API with Qdrant vector storage and OpenAI embeddings.",
    )

    app.include_router(health.router)
    app.include_router(embeddings.router)
    app.include_router(collections.router)
    app.include_router(documents.router)
    app.include_router(search.router)

    return app


app = create_app()
