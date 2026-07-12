from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress

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
    get_session_factory,
    init_engine,
)
from app.routers import (
    call_jobs,
    call_summaries,
    clients,
    collections,
    consumers,
    documents,
    embeddings,
    health,
    search,
    voice_agent_config,
    voice_agent_schedules,
)
from app.services.call_job_service import build_call_job_service
from app.services.voice_agent_schedule_poller import run_voice_agent_schedule_poller
from app.services.voice_agent_schedule_service import VoiceAgentScheduleService

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

    poller_task: asyncio.Task | None = None
    if settings.voice_agent_schedule_enabled and not os.getenv("PYTEST_CURRENT_TEST"):
        schedule_service = VoiceAgentScheduleService(
            session_factory=get_session_factory(),
            call_job_service=build_call_job_service(settings),
        )
        poller_task = asyncio.create_task(
            run_voice_agent_schedule_poller(
                schedule_service,
                enabled=True,
            )
        )

    yield

    if poller_task is not None:
        poller_task.cancel()
        with suppress(asyncio.CancelledError):
            await poller_task

    await dispose_engine()
    reset_rag_clients()
    logger.info("database engine disposed")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "RAG REST API with Qdrant vector storage, consumer management, "
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
    app.include_router(consumers.router)
    app.include_router(call_summaries.router)
    app.include_router(voice_agent_config.router)
    app.include_router(voice_agent_schedules.router)
    app.include_router(clients.router)
    app.include_router(call_jobs.router)

    return app


app = create_app()
