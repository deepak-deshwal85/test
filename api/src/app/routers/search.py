from __future__ import annotations

import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.core.dependencies import get_search_service, verify_api_key
from app.core.qdrant_errors import is_qdrant_connection_error, qdrant_unavailable_detail
from app.schemas.search import SearchHitResponse, SearchRequest, SearchResponse
from app.services.search_service import SearchService

logger = logging.getLogger("relaydesk-api")

router = APIRouter(
    prefix="/v1",
    tags=["search"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/search", response_model=SearchResponse)
def search(
    body: SearchRequest,
    service: Annotated[SearchService, Depends(get_search_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SearchResponse:
    started = time.perf_counter()
    try:
        hits, collection = service.search(
            query=body.query,
            max_results=body.max_results,
            collection=body.collection,
            phone_number=body.phone_number,
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

    logger.info(
        "POST /v1/search collection=%s hits=%d total_ms=%.0f query=%r",
        collection,
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
        collection=collection,
    )
