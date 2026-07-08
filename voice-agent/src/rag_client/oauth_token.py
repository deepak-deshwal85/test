from __future__ import annotations

import asyncio
import logging
import os
import time

import httpx

logger = logging.getLogger("relaydesk-agent")


class CognitoTokenProvider:
    """Fetches and caches Cognito OAuth2 client-credentials access tokens."""

    def __init__(
        self,
        *,
        token_url: str,
        client_id: str,
        client_secret: str,
        scope: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._scope = scope
        self._http_client = http_client
        self._owns_client = http_client is None
        self._access_token: str | None = None
        self._expires_at = 0.0
        self._lock = asyncio.Lock()

    def _client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(15.0))
            self._owns_client = True
        return self._http_client

    async def aclose(self) -> None:
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def get_access_token(self) -> str:
        async with self._lock:
            now = time.time()
            if self._access_token and now < self._expires_at - 30:
                return self._access_token

            response = await self._client().post(
                self._token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "scope": self._scope,
                },
                headers={"content-type": "application/x-www-form-urlencoded"},
            )
            if response.status_code >= 400:
                logger.error(
                    "cognito token request failed status=%s body=%s",
                    response.status_code,
                    response.text[:300],
                )
            response.raise_for_status()
            payload = response.json()
            token = str(payload.get("access_token", "")).strip()
            if not token:
                raise RuntimeError("Cognito token response missing access_token")
            expires_in = int(payload.get("expires_in", 3600))
            self._access_token = token
            self._expires_at = now + expires_in
            logger.debug("cognito access token refreshed expires_in=%s", expires_in)
            return token


_provider: CognitoTokenProvider | None = None


def get_cognito_token_provider() -> CognitoTokenProvider | None:
    global _provider
    token_url = os.getenv("COGNITO_TOKEN_URL", "").strip()
    client_id = os.getenv("COGNITO_CLIENT_ID", "").strip()
    client_secret = os.getenv("COGNITO_CLIENT_SECRET", "").strip()
    scope = os.getenv("COGNITO_SCOPE", "relaydesk-api/access").strip()
    if not token_url or not client_id or not client_secret:
        missing = [
            name
            for name, value in (
                ("COGNITO_TOKEN_URL", token_url),
                ("COGNITO_CLIENT_ID", client_id),
                ("COGNITO_CLIENT_SECRET", client_secret),
            )
            if not value
        ]
        logger.warning("cognito m2m auth disabled; missing env: %s", ", ".join(missing))
        return None
    if _provider is None:
        _provider = CognitoTokenProvider(
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            scope=scope,
        )
    return _provider
