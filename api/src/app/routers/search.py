from __future__ import annotations

import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.core.collections import collection_from_phone
from app.core.dependencies import (
    get_client_repository,
    get_search_service,
    verify_access_token,
)
from app.core.oauth import AuthenticatedPrincipal
from app.core.qdrant_errors import is_qdrant_connection_error, qdrant_unavailable_detail
from app.core.tenant import is_scope_unrestricted, resolve_client_scope, verify_client_email_scope
from app.db.postgres.client_repository import ClientRepository
from app.schemas.search import SearchHitResponse, SearchRequest, SearchResponse
from app.services.search_service import SearchService

logger = logging.getLogger("relaydesk-api")

router = APIRouter(
    prefix="/v1",
    tags=["search"],
    dependencies=[Depends(verify_access_token)],
)


@router.post("/search", response_model=SearchResponse)
async def search(
    body: SearchRequest,
    service: Annotated[SearchService, Depends(get_search_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    principal: Annotated[AuthenticatedPrincipal, Depends(verify_access_token)],
    repository: Annotated[ClientRepository, Depends(get_client_repository)],
) -> SearchResponse:
    client = None
    if is_scope_unrestricted(principal) and not body.client_email_id:
        scope = resolve_client_scope(principal, client_email_id=None, client=None)
    else:
        if not body.client_email_id:
            raise HTTPException(status_code=400, detail="client_email_id is required")
        await verify_client_email_scope(principal, body.client_email_id, repository)
        client = await repository.get_by_email(body.client_email_id)
        scope = resolve_client_scope(
            principal,
            client_email_id=body.client_email_id,
            client=client,
        )

    phone_number = body.phone_number
    collection = body.collection
    if not scope.unrestricted:
        phone_number = scope.client_business_phone_number
        collection = scope.collection_name
    elif scope.client_business_phone_number:
        phone_number = scope.client_business_phone_number
        collection = scope.collection_name
    elif body.client_email_id and client is not None:
        phone_number = client.client_business_phone_number
        collection = (
            collection_from_phone(client.client_business_phone_number)
            if client.client_business_phone_number
            else None
        )

    started = time.perf_counter()
    try:
        hits, resolved_collection = service.search(
            query=body.query,
            max_results=body.max_results,
            collection=collection,
            phone_number=phone_number,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        if is_qdrant_connection_error(exc):
            raise HTTPException(
                status_code=503, detail=qdrant_unavailable_detail(settings)
            ) from exc
        logger.exception("search failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    resolved_phone = phone_number
    if resolved_phone is None and resolved_collection:
        if resolved_collection.startswith("phone_"):
            resolved_phone = resolved_collection.removeprefix("phone_")

    logger.info(
        "POST /v1/search collection=%s hits=%d total_ms=%.0f query=%r",
        resolved_collection,
        len(hits),
        (time.perf_counter() - started) * 1000,
        body.query[:80],
    )
    return SearchResponse(
        hits=[
            SearchHitResponse(
                text=hit.text,
                score=hit.score,
                source_uri=hit.source_uri,
            )
            for hit in hits
        ],
        count=len(hits),
        collection=resolved_collection,
        client_business_phone_number=resolved_phone,
        client_email_id=scope.client_email_id,
    )
