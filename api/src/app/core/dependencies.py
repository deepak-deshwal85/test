from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings
from app.db.embedding_provider import EmbeddingProviderFactory
from app.db.qdrant_repository import QdrantRepository
from app.services.collection_service import CollectionService
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.services.search_service import SearchService


def get_qdrant_repository(
    settings: Annotated[Settings, Depends(get_settings)],
) -> QdrantRepository:
    return QdrantRepository(settings)


def get_embedding_provider_factory(
    settings: Annotated[Settings, Depends(get_settings)],
) -> EmbeddingProviderFactory:
    return EmbeddingProviderFactory(settings)


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
