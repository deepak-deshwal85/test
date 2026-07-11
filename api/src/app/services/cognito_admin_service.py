from __future__ import annotations

import asyncio
import logging
from functools import lru_cache

from app.core.config import Settings

logger = logging.getLogger("relaydesk-api")

RELAYDESK_ROLE_GROUPS = (
    "guest-clients",
    "approved-clients",
    "relaydesk-admins",
)


class CognitoAdminError(RuntimeError):
    pass


class CognitoAdminService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def enabled(self) -> bool:
        return bool(
            not self._settings.oauth_disabled
            and self._settings.cognito_region
            and self._settings.cognito_user_pool_id
        )

    def _client(self):
        import boto3

        return boto3.client(
            "cognito-idp",
            region_name=self._settings.cognito_region,
        )

    def _find_username_by_email(self, email: str) -> str:
        normalized = email.strip().lower()
        response = self._client().list_users(
            UserPoolId=self._settings.cognito_user_pool_id,
            Filter=f'email = "{normalized}"',
            Limit=10,
        )
        users = response.get("Users") or []
        if not users:
            raise CognitoAdminError(
                f"No Cognito user found for {normalized!r}. "
                "Ask them to sign in once via SSO, then retry."
            )
        if len(users) > 1:
            raise CognitoAdminError(f"Multiple Cognito users match email {normalized!r}")
        username = users[0].get("Username")
        if not username:
            raise CognitoAdminError(f"Cognito user for {normalized!r} has no Username")
        return str(username)

    def _remove_from_role_groups(self, username: str) -> None:
        client = self._client()
        for group_name in RELAYDESK_ROLE_GROUPS:
            try:
                client.admin_remove_user_from_group(
                    UserPoolId=self._settings.cognito_user_pool_id,
                    Username=username,
                    GroupName=group_name,
                )
            except client.exceptions.ResourceNotFoundException:
                continue
            except client.exceptions.ClientError as exc:
                code = exc.response.get("Error", {}).get("Code", "")
                if code in {"UserNotFoundException", "ResourceNotFoundException"}:
                    continue
                raise CognitoAdminError(str(exc)) from exc

    def _promote_to_approved_sync(self, email: str) -> None:
        username = self._find_username_by_email(email)
        self._remove_from_role_groups(username)
        self._client().admin_add_user_to_group(
            UserPoolId=self._settings.cognito_user_pool_id,
            Username=username,
            GroupName="approved-clients",
        )
        logger.info("promoted %r to approved-clients in Cognito", email)

    async def promote_to_approved(self, email: str) -> None:
        if not self.enabled:
            logger.info(
                "skipping Cognito promotion for %r (OAuth disabled or not configured)",
                email,
            )
            return
        await asyncio.to_thread(self._promote_to_approved_sync, email)

    def _delete_user_sync(self, email: str) -> None:
        username = self._find_username_by_email(email)
        self._client().admin_delete_user(
            UserPoolId=self._settings.cognito_user_pool_id,
            Username=username,
        )
        logger.info("deleted Cognito user %r (%s)", email, username)

    async def delete_user(self, email: str) -> None:
        if not self.enabled:
            logger.info(
                "skipping Cognito delete for %r (OAuth disabled or not configured)",
                email,
            )
            return
        await asyncio.to_thread(self._delete_user_sync, email)


@lru_cache
def get_cognito_admin_service(settings: Settings | None = None) -> CognitoAdminService:
    from app.core.config import get_settings

    return CognitoAdminService(settings or get_settings())
