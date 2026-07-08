"use client";

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`/api/backend/${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const text = await response.text();
    let detail = text;
    try {
      const json = JSON.parse(text) as { detail?: string };
      detail = json.detail ?? text;
    } catch {
      /* use raw text */
    }
    throw new Error(detail || `Request failed (${response.status})`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function apiUpload<T>(
  path: string,
  file: File,
): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`/api/backend/${path}`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Upload failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}
