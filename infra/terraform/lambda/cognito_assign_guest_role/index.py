"""Cognito Post Confirmation trigger: assign new users to guest-clients."""

from __future__ import annotations

import os

GUEST_GROUP = os.environ.get("GUEST_GROUP", "guest-clients")
ELEVATED_GROUPS = tuple(
    group.strip()
    for group in os.environ.get(
        "ELEVATED_GROUPS", "approved-clients,relaydesk-admins"
    ).split(",")
    if group.strip()
)
ASSIGN_ON_TRIGGER = "PostConfirmation_ConfirmSignUp"


def _cognito_client():
    import boto3

    return boto3.client("cognito-idp")


def _existing_groups(user_pool_id: str, username: str) -> set[str]:
    response = _cognito_client().admin_list_groups_for_user(
        UserPoolId=user_pool_id,
        Username=username,
    )
    return {group["GroupName"] for group in response.get("Groups", [])}


def handler(event, _context):
    # Cognito requires returning the event object unchanged.
    if event.get("triggerSource") != ASSIGN_ON_TRIGGER:
        return event

    user_pool_id = event["userPoolId"]
    username = event["userName"]
    groups = _existing_groups(user_pool_id, username)

    if groups.intersection(ELEVATED_GROUPS):
        return event

    if GUEST_GROUP not in groups:
        _cognito_client().admin_add_user_to_group(
            UserPoolId=user_pool_id,
            Username=username,
            GroupName=GUEST_GROUP,
        )

    return event
