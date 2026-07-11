"use client";

import { signIn, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { ArrowRight, Radio } from "lucide-react";
import { Button, ErrorBanner, Spinner } from "@/components/ui";
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
    return (
      <div className="mt-8 flex items-center gap-2 text-sm text-muted-foreground">
        <Spinner />
        Loading session…
      </div>
    );
  }

  if (status === "authenticated") {
    router.replace(callbackUrl);
    return null;
  }

  return (
    <>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
        {skipSsoInLocal
          ? "Local development mode — SSO is bypassed."
          : "Sign in with your organization account to continue."}
      </p>

      {authError ? (
        <ErrorBanner
          className="mt-6"
          message="Sign-in failed. Check OAuth client configuration and callback URLs."
        />
      ) : null}

      <div className="mt-8">
        {skipSsoInLocal ? (
          <Button
            type="button"
            className="w-full"
            size="lg"
            onClick={() => signIn("credentials", { callbackUrl })}
          >
            Continue in local mode
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Button>
        ) : useCognito ? (
          <Button
            type="button"
            className="w-full"
            size="lg"
            onClick={() => signIn("cognito", { callbackUrl })}
          >
            Continue with SSO
            <ArrowRight className="h-4 w-4" aria-hidden />
          </Button>
        ) : (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            Cognito is not configured. Set COGNITO_ISSUER, COGNITO_CLIENT_ID, and
            COGNITO_CLIENT_SECRET, or enable local mode with AUTH_DISABLE_SSO=true.
          </div>
        )}
      </div>
    </>
  );
}

export function LoginBrand() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm">
        <Radio className="h-5 w-5" aria-hidden />
      </div>
      <div>
        <p className="text-sm font-semibold text-foreground">RelayDesk</p>
        <p className="text-xs text-muted-foreground">Voice AI operations</p>
      </div>
    </div>
  );
}
