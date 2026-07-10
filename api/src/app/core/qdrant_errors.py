from __future__ import annotations

from httpx import ConnectError
from qdrant_client.http.exceptions import ResponseHandlingException

from app.core.config import Settings


def is_qdrant_connection_error(exc: BaseException) -> bool:
    if isinstance(exc, ConnectError):
        return True
    if isinstance(exc, ResponseHandlingException):
        cause = exc.__cause__
        if isinstance(cause, ConnectError):
            return True
        message = str(exc).lower()
        return "refused" in message or "10061" in message
    message = str(exc).lower()
    return "connection refused" in message or "10061" in message


def qdrant_unavailable_detail(settings: Settings) -> str:
    cluster = settings.qdrant_cluster_name or "unknown"
    return (
        f"Qdrant Cloud cluster {cluster} is not reachable at {settings.qdrant_url}. "
        "Check QDRANT_CLUSTER_ENDPOINT and QDRANT_API_KEY."
    )
