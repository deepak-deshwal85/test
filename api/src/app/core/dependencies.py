from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.embedding_provider import EmbeddingProviderFactory
from app.db.postgres.customer_repository import CustomerRepository
from app.db.postgres.session import get_db_session
from app.db.qdrant_repository import QdrantRepository
from app.services.call_job_service import CallJobService, build_call_job_service
from app.services.collection_service import CollectionService
from app.services.customer_service import CustomerService
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.services.search_service import SearchService

_call_job_service: CallJobService | None = None
_qdrant_repository: QdrantRepository | None = None
_embedding_provider_factory: EmbeddingProviderFactory | None = None


def get_qdrant_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> QdrantRepository:
    global _qdrant_repository
    if _qdrant_repository is None:
        _qdrant_repository = QdrantRepository(settings)
    return _qdrant_repository


def get_embedding_provider_factory(
    settings: Annotated[Settings, Depends(get_settings)],
) -> EmbeddingProviderFactory:
    global _embedding_provider_factory
    if _embedding_provider_factory is None:
        _embedding_provider_factory = EmbeddingProviderFactory(settings)
    return _embedding_provider_factory


def get_embedding_service(
    settings: Annotated[Settings, Depends(get_settings)],
    provider_factory: Annotated[
        EmbeddingProviderFactory, Depends(get_embedding_provider_factory)
    ],
) -> EmbeddingService:
    return EmbeddingService(settings, provider_factory)


def get_document_service(
    settings: Annotated[Settings, Depends(get_settings)],
    qdrant: Annotated[QdrantRepository, Depends(get_qdrant_repository)],
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
) -> DocumentService:
    return DocumentService(settings, qdrant, embedding_service)


def get_search_service(
    settings: Annotated[Settings, Depends(get_settings)],
    qdrant: Annotated[QdrantRepository, Depends(get_qdrant_repository)],
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
) -> SearchService:
    return SearchService(settings, qdrant, embedding_service)


def get_collection_service(
    qdrant: Annotated[QdrantRepository, Depends(get_qdrant_repository)],
) -> CollectionService:
    return CollectionService(qdrant)


async def get_customer_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CustomerRepository:
    return CustomerRepository(session)


async def get_customer_service(
    repository: Annotated[CustomerRepository, Depends(get_customer_repository)],
) -> CustomerService:
    return CustomerService(repository)


def get_call_job_service(
    settings: Annotated[Settings, Depends(get_settings)],
) -> CallJobService:
    global _call_job_service
    if _call_job_service is None:
        _call_job_service = build_call_job_service(settings)
    return _call_job_service


def reset_call_job_service() -> None:
    global _call_job_service
    _call_job_service = None


def reset_rag_clients() -> None:
    global _qdrant_repository, _embedding_provider_factory
    _qdrant_repository = None
    _embedding_provider_factory = None


def verify_api_key(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    if not settings.rag_api_key:
        return

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    token = authorization.removeprefix("Bearer ").strip()
    if token != settings.rag_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
