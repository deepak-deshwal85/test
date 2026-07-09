from __future__ import annotations

from enum import Enum


class RelayDeskRole(str, Enum):
    GUEST = "guest-clients"
    APPROVED = "approved-clients"
    ADMIN = "relaydesk-admins"


class Permission(str, Enum):
    READ = "read"
    DOCUMENT_WRITE = "document_write"
    ADMIN = "admin"


ROLE_PERMISSIONS: dict[RelayDeskRole, frozenset[Permission]] = {
    RelayDeskRole.GUEST: frozenset({Permission.READ}),
    RelayDeskRole.APPROVED: frozenset(
        {Permission.READ, Permission.DOCUMENT_WRITE}
    ),
    RelayDeskRole.ADMIN: frozenset(
        {Permission.READ, Permission.DOCUMENT_WRITE, Permission.ADMIN}
    ),
}

ROLE_PRIORITY: tuple[RelayDeskRole, ...] = (
    RelayDeskRole.ADMIN,
    RelayDeskRole.APPROVED,
    RelayDeskRole.GUEST,
)


def resolve_role(
    groups: frozenset[str],
    *,
    default_guest: bool = False,
) -> RelayDeskRole | None:
    for role in ROLE_PRIORITY:
        if role.value in groups:
            return role
    if default_guest:
        return RelayDeskRole.GUEST
    return None


def role_has_permission(role: RelayDeskRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS[role]
