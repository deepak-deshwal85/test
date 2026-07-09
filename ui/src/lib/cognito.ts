import { resolveRole, type RelayDeskRole } from "@/lib/roles";

export function decodeJwtPayload(token: string): Record<string, unknown> {
  const segment = token.split(".")[1];
  if (!segment) {
    return {};
  }

  const normalized = segment.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(
    normalized.length + ((4 - (normalized.length % 4)) % 4),
    "=",
  );
  const json = Buffer.from(padded, "base64").toString("utf8");
  return JSON.parse(json) as Record<string, unknown>;
}

export function cognitoGroupsFromIdToken(idToken: string): string[] {
  const payload = decodeJwtPayload(idToken);
  const groups = payload["cognito:groups"];

  if (Array.isArray(groups)) {
    return groups.map(String);
  }
  if (typeof groups === "string") {
    return groups.split(",").map((group) => group.trim()).filter(Boolean);
  }
  return [];
}

export function relayDeskRoleFromIdToken(idToken: string): RelayDeskRole {
  return resolveRole(cognitoGroupsFromIdToken(idToken));
}

export function emailFromIdToken(idToken: string): string | null {
  const payload = decodeJwtPayload(idToken);
  const email = payload.email;
  return typeof email === "string" && email.includes("@")
    ? email.toLowerCase()
    : null;
}

export function nameFromIdToken(idToken: string): string | null {
  const payload = decodeJwtPayload(idToken);
  const name = payload.name;
  return typeof name === "string" && name.trim() ? name.trim() : null;
}
