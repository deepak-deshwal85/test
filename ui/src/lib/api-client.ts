"use client";

type ValidationErrorItem = {
  loc?: unknown[];
  msg?: string;
  type?: string;
};

export function formatApiErrorDetail(detail: unknown): string {
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }
        if (item && typeof item === "object") {
          const err = item as ValidationErrorItem;
          const field = Array.isArray(err.loc)
            ? err.loc
                .filter((part) => part !== "body" && part !== "query")
                .join(".")
            : "";
          const msg = err.msg ?? JSON.stringify(item);
          return field ? `${field}: ${msg}` : msg;
        }
        return String(item);
      })
      .join("; ");
  }

  if (detail && typeof detail === "object") {
    const record = detail as Record<string, unknown>;
    if (typeof record.message === "string") {
      return record.message;
    }
    if (typeof record.detail === "string") {
      return record.detail;
    }
    try {
      return JSON.stringify(detail);
    } catch {
      return "Request failed";
    }
  }

  return String(detail);
}

export function errorMessageFromUnknown(
  error: unknown,
  fallback: string,
): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  if (typeof error === "string") {
    return error;
  }
  return fallback;
}

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
    let detail: unknown = text;
    try {
      const json = JSON.parse(text) as { detail?: unknown };
      if (json.detail !== undefined) {
        detail = json.detail;
      }
    } catch {
      /* use raw text */
    }
    const message = formatApiErrorDetail(detail);
    throw new Error(message || `Request failed (${response.status})`);
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
    let detail: unknown = text;
    try {
      const json = JSON.parse(text) as { detail?: unknown };
      if (json.detail !== undefined) {
        detail = json.detail;
      }
    } catch {
      /* use raw text */
    }
    const message = formatApiErrorDetail(detail);
    throw new Error(message || `Upload failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}
