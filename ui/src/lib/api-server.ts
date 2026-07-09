import { auth } from "@/lib/auth";
import { isAuthDisabledForLocal, resolveApiBaseUrl } from "@/lib/runtime-config";

const API_URL = resolveApiBaseUrl();
const skipSsoInLocal = isAuthDisabledForLocal();

async function authHeaders(): Promise<Headers> {
  const headers = new Headers({ "content-type": "application/json" });
  if (skipSsoInLocal) {
    return headers;
  }

  const session = await auth();
  if (session?.accessToken) {
    headers.set("authorization", `Bearer ${session.accessToken}`);
  }
  return headers;
}

export async function serverApiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const session = await auth();
  if (!skipSsoInLocal && !session?.user) {
    throw new Error("Unauthorized");
  }

  const headers = await authHeaders();
  for (const [key, value] of new Headers(init?.headers).entries()) {
    headers.set(key, value);
  }

  const sessionEmail = session?.user?.email?.trim();
  if (sessionEmail) {
    headers.set("x-relaydesk-user-email", sessionEmail);
  }

  const response = await fetch(`${API_URL}/${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed (${response.status})`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
