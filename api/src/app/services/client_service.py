from __future__ import annotations

from app.db.postgres.client_repository import ClientRepository
from app.schemas.clients import (
    ClientAdminListResponse,
    ClientAdminProfileResponse,
    ClientListResponse,
    ClientProfileResponse,
    ClientProfileUpsertRequest,
)
from app.services.cognito_admin_service import CognitoAdminError, CognitoAdminService


class ClientService:
    def __init__(
        self,
        repository: ClientRepository,
        cognito_admin: CognitoAdminService | None = None,
    ) -> None:
        self._repository = repository
        self._cognito_admin = cognito_admin

    @staticmethod
    def _to_response(client) -> ClientProfileResponse:
        return ClientProfileResponse(
            id=client.id,
            client_phone_number=client.client_phone_number,
            client_business_phone_number=client.client_business_phone_number,
            client_name=client.client_name,
            client_email_id=client.client_email_id,
            created_at=client.created_at,
        )

    @staticmethod
    def _to_admin_response(client) -> ClientAdminProfileResponse:
        return ClientAdminProfileResponse(
            id=client.id,
            client_phone_number=client.client_phone_number,
            client_business_phone_number=client.client_business_phone_number,
            client_name=client.client_name,
            client_email_id=client.client_email_id,
            created_at=client.created_at,
            is_approved=bool(client.client_business_phone_number),
            cognito_sub=client.cognito_sub,
        )

    async def get_profile(self, client_email_id: str) -> ClientProfileResponse | None:
        client = await self._repository.get_by_email(client_email_id)
        return self._to_response(client) if client else None

    async def get_profile_for_principal(
        self,
        *,
        cognito_sub: str,
        client_email_id: str | None = None,
    ) -> ClientProfileResponse | None:
        client = await self._repository.get_by_cognito_sub(cognito_sub)
        if client is None and client_email_id:
            client = await self._repository.get_by_email(client_email_id)
        return self._to_response(client) if client else None

    async def ensure_on_sign_in(
        self,
        *,
        client_email_id: str,
        cognito_sub: str,
    ) -> ClientProfileResponse:
        client = await self._repository.ensure_on_sign_in(
            client_email_id=client_email_id,
            cognito_sub=cognito_sub,
        )
        return self._to_response(client)

    async def upsert_profile(
        self,
        body: ClientProfileUpsertRequest,
        *,
        client_email_id: str,
        cognito_sub: str | None = None,
    ) -> ClientProfileResponse:
        client = await self._repository.upsert_personal_profile(
            client_name=body.client_name,
            client_phone_number=body.client_phone_number,
            client_email_id=client_email_id,
            cognito_sub=cognito_sub,
        )
        return self._to_response(client)

    async def set_business_phone(
        self,
        *,
        client_email_id: str,
        client_business_phone_number: str,
    ) -> ClientProfileResponse:
        client = await self._repository.set_business_phone(
            client_email_id=client_email_id,
            client_business_phone_number=client_business_phone_number,
        )
        return self._to_response(client)

    async def list_clients(self) -> ClientListResponse:
        clients = await self._repository.list_all()
        responses = [self._to_response(client) for client in clients]
        return ClientListResponse(clients=responses, count=len(responses))

    async def list_clients_admin(self) -> ClientAdminListResponse:
        clients = await self._repository.list_all()
        responses = [self._to_admin_response(client) for client in clients]
        return ClientAdminListResponse(clients=responses, count=len(responses))

    async def approve_client(
        self,
        *,
        client_email_id: str,
        client_business_phone_number: str,
    ) -> ClientAdminProfileResponse:
        if self._cognito_admin is not None:
            try:
                await self._cognito_admin.promote_to_approved(client_email_id)
            except CognitoAdminError as exc:
                raise ValueError(str(exc)) from exc

        try:
            client = await self._repository.set_business_phone(
                client_email_id=client_email_id,
                client_business_phone_number=client_business_phone_number,
            )
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        return self._to_admin_response(client)
