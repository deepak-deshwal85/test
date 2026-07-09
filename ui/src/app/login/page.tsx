import { LoginClient } from "@/components/login-client";

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
        <LoginClient
          callbackUrl={callbackUrl}
          useCognito={useCognito}
          authError={params.error}
        />
      </div>
    </div>
  );
}
