import { auth } from "@/lib/auth";

const API_URL = process.env.RELAYDESK_API_URL ?? "http://127.0.0.1:8090";

async function authHeaders(): Promise<Headers> {
  const session = await auth();
  const headers = new Headers({ "content-type": "application/json" });
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
  if (!session?.user) {
    throw new Error("Unauthorized");
  }

  const headers = await authHeaders();
  for (const [key, value] of new Headers(init?.headers).entries()) {
    headers.set(key, value);
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
