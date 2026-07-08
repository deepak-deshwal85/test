import { signIn } from "@/lib/auth";
import { isAuthDisabledForLocal } from "@/lib/runtime-config";

const skipSsoInLocal = isAuthDisabledForLocal();

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ callbackUrl?: string; error?: string }>;
}) {
  const params = await searchParams;
  const callbackUrl = params.callbackUrl ?? "/";
  const useCognito = Boolean(process.env.COGNITO_ISSUER);

  return (
    <div className="flex min-h-dvh items-center justify-center px-4">
      <div className="w-full max-w-md rounded-3xl border border-white/70 bg-white/90 p-8 shadow-xl backdrop-blur">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-600">
          RelayDesk
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">Sign in</h1>
        <p className="mt-2 text-sm text-slate-600">
          {skipSsoInLocal
            ? "Local mode enabled — SSO is bypassed for local development."
            : "Use your organization SSO (via Cognito) to access the console."}
        </p>

        {params.error ? (
          <div className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            Sign-in failed. Check OAuth client configuration and callback URLs.
          </div>
        ) : null}

        <div className="mt-8 space-y-3">
          {skipSsoInLocal ? (
            <form
              action={async () => {
                "use server";
                await signIn("credentials", { redirectTo: callbackUrl });
              }}
            >
              <button
                type="submit"
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-4 py-3 text-sm font-medium text-white hover:bg-brand-700"
              >
                Continue in local mode
              </button>
            </form>
          ) : useCognito ? (
            <form
              action={async () => {
                "use server";
                await signIn("cognito", { redirectTo: callbackUrl });
              }}
            >
              <button
                type="submit"
                className="flex w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-4 py-3 text-sm font-medium text-white hover:bg-brand-700"
              >
                Continue with SSO
              </button>
            </form>
          ) : (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              Cognito is not configured. Set COGNITO_ISSUER, COGNITO_CLIENT_ID,
              and COGNITO_CLIENT_SECRET, or enable local mode with
              AUTH_DISABLE_SSO=true.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
