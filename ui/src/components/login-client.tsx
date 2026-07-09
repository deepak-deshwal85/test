"use client";

import { signIn, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { isAuthDisabledForLocal } from "@/lib/runtime-config";

export function LoginClient({
  callbackUrl,
  useCognito,
  authError,
}: {
  callbackUrl: string;
  useCognito: boolean;
  authError?: string;
}) {
  const router = useRouter();
  const { status } = useSession();
  const skipSsoInLocal = isAuthDisabledForLocal();

  if (status === "loading") {
    return <p className="mt-8 text-sm text-slate-500">Loading…</p>;
  }

  if (status === "authenticated") {
    router.replace(callbackUrl);
    return null;
  }

  return (
    <>
      <p className="mt-2 text-sm text-slate-600">
        {skipSsoInLocal
          ? "Local mode enabled — SSO is bypassed for local development."
          : "Sign in with SSO to access the console."}
      </p>

      {authError ? (
        <div className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Sign-in failed. Check OAuth client configuration and callback URLs.
        </div>
      ) : null}

      <div className="mt-8 space-y-3">
        {skipSsoInLocal ? (
          <button
            type="button"
            onClick={() => signIn("credentials", { callbackUrl })}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-4 py-3 text-sm font-medium text-white hover:bg-brand-700"
          >
            Continue in local mode
          </button>
        ) : useCognito ? (
          <button
            type="button"
            onClick={() => signIn("cognito", { callbackUrl })}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-4 py-3 text-sm font-medium text-white hover:bg-brand-700"
          >
            Continue with SSO
          </button>
        ) : (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Cognito is not configured. Set COGNITO_ISSUER, COGNITO_CLIENT_ID,
            and COGNITO_CLIENT_SECRET, or enable local mode with
            AUTH_DISABLE_SSO=true.
          </div>
        )}
      </div>
    </>
  );
}
