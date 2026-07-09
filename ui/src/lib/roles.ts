export const RELAYDESK_ROLES = [
  "guest-clients",
  "approved-clients",
  "relaydesk-admins",
] as const;

export type RelayDeskRole = (typeof RELAYDESK_ROLES)[number];

export type Permission = "read" | "document_write" | "admin";

const ROLE_PERMISSIONS: Record<RelayDeskRole, Permission[]> = {
  "guest-clients": ["read"],
  "approved-clients": ["read", "document_write"],
  "relaydesk-admins": ["read", "document_write", "admin"],
};

const ROLE_PRIORITY: RelayDeskRole[] = [
  "relaydesk-admins",
  "approved-clients",
  "guest-clients",
];

export function resolveRole(groups: string[]): RelayDeskRole {
  for (const role of ROLE_PRIORITY) {
    if (groups.includes(role)) {
      return role;
    }
  }
  return "guest-clients";
}

export function hasPermission(
  role: RelayDeskRole | null | undefined,
  permission: Permission,
): boolean {
  const effectiveRole = role ?? "guest-clients";
  return ROLE_PERMISSIONS[effectiveRole].includes(permission);
}

export function roleLabel(role: RelayDeskRole): string {
  switch (role) {
    case "guest-clients":
      return "Guest";
    case "approved-clients":
      return "Approved client";
    case "relaydesk-admins":
      return "Admin";
  }
}
