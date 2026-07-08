const LOCAL_API_DEFAULT = "http://127.0.0.1:8090";

function normalizeTarget(value: string | undefined): "auto" | "local" | "aws" {
  const target = (value ?? "auto").toLowerCase();
  if (target === "local" || target === "aws") {
    return target;
  }
  return "auto";
}

export function isAuthDisabledForLocal(): boolean {
  return process.env.AUTH_DISABLE_SSO === "true";
}

export function resolveApiBaseUrl(): string {
  const explicitUrl = process.env.RELAYDESK_API_URL;
  if (explicitUrl && explicitUrl.trim()) {
    return explicitUrl.trim();
  }

  const target = normalizeTarget(process.env.RELAYDESK_API_TARGET);
  const localUrl = process.env.RELAYDESK_API_URL_LOCAL ?? LOCAL_API_DEFAULT;
  const awsUrl = process.env.RELAYDESK_API_URL_AWS;

  if (target === "local") {
    return localUrl;
  }
  if (target === "aws") {
    return awsUrl?.trim() || localUrl;
  }

  if (process.env.NODE_ENV === "production") {
    return awsUrl?.trim() || localUrl;
  }
  return localUrl;
}
