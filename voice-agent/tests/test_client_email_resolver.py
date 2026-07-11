import json
import sys
from pathlib import Path
from unittest.mock import patch

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from client_email_resolver import resolve_client_email, resolve_client_email_by_phone
from rag_client.config import RagClientSettings


def test_resolve_client_email_prefers_metadata():
    async def _run() -> None:
        email = await resolve_client_email(
            metadata_email="meta@example.com",
            config_email="config@example.com",
            phone_digits="91911171366880",
        )
        assert email == "meta@example.com"

    import asyncio

    asyncio.run(_run())


def test_resolve_client_email_falls_back_to_config():
    async def _run() -> None:
        email = await resolve_client_email(
            metadata_email=None,
            config_email="config@example.com",
            phone_digits="91911171366880",
        )
        assert email == "config@example.com"

    import asyncio

    asyncio.run(_run())


def test_resolve_client_email_by_phone_calls_api():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/clients/resolve-by-phone"
        assert request.url.params["phone_number"] == "91911171366880"
        return httpx.Response(
            200,
            json={
                "client_email_id": "client@example.com",
                "client_name": "Acme",
                "client_business_phone_number": "91911171366880",
                "collection_name": "client@example.com",
            },
        )

    transport = httpx.MockTransport(handler)

    async def _run() -> None:
        client = httpx.AsyncClient(transport=transport, base_url="http://rag.test")
        resolved = await resolve_client_email_by_phone(
            phone_digits="91911171366880",
            base_url="http://rag.test",
            http_client=client,
        )
        assert resolved is not None
        assert resolved.client_email_id == "client@example.com"
        await client.aclose()

    import asyncio

    asyncio.run(_run())


def test_resolve_client_email_uses_api_when_no_metadata_or_config():
    settings = RagClientSettings(
        backend="qdrant",
        max_results=3,
        rag_api_base_url="http://rag.test",
        min_score=0.3,
    )

    async def fake_resolve(*, phone_digits, base_url, http_client=None):
        assert phone_digits == "91911171366880"
        from client_email_resolver import ResolvedClientEmail

        return ResolvedClientEmail(
            client_email_id="client@example.com",
            collection_name="client@example.com",
        )

    async def _run() -> None:
        with patch(
            "client_email_resolver.resolve_client_email_by_phone",
            side_effect=fake_resolve,
        ):
            email = await resolve_client_email(
                metadata_email=None,
                config_email=None,
                phone_digits="91911171366880",
                settings=settings,
            )
        assert email == "client@example.com"

    import asyncio

    asyncio.run(_run())
