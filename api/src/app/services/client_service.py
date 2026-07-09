from __future__ import annotations

from app.db.postgres.client_repository import ClientRepository
from app.schemas.clients import ClientProfileResponse, ClientProfileUpsertRequest


class ClientService:
    def __init__(self, repository: ClientRepository) -> None:
        self._repository = repository

    @staticmethod
    def _to_response(client) -> ClientProfileResponse:
        return ClientProfileResponse(
            id=client.id,
            client_phone_number=client.client_phone_number,
            client_name=client.client_name,
            client_email_id=client.client_email_id,
            created_at=client.created_at,
        )

    async def get_profile(self, client_email_id: str) -> ClientProfileResponse | None:
        client = await self._repository.get_by_email(client_email_id)
        return self._to_response(client) if client else None

    async def upsert_profile(
        self,
        body: ClientProfileUpsertRequest,
        *,
        cognito_sub: str | None = None,
    ) -> ClientProfileResponse:
        client = await self._repository.upsert_profile(
            client_name=body.client_name,
            client_phone_number=body.client_phone_number,
            client_email_id=body.client_email_id,
            cognito_sub=cognito_sub,
        )
        return self._to_response(client)
