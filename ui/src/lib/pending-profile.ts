const STORAGE_KEY = "relaydesk.pendingProfile";

export type PendingProfile = {
  clientName: string;
  clientPhone: string;
};

export function writePendingProfile(profile: PendingProfile): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(profile));
}

export function readPendingProfile(): PendingProfile | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as PendingProfile;
    if (
      typeof parsed.clientName === "string" &&
      typeof parsed.clientPhone === "string"
    ) {
      return parsed;
    }
  } catch {
    /* ignore */
  }
  return null;
}

export function clearPendingProfile(): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(STORAGE_KEY);
}
