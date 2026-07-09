import { SignupClient } from "@/components/signup-client";

export default async function SignupPage({
  searchParams,
}: {
  searchParams: Promise<{ callbackUrl?: string }>;
}) {
  const params = await searchParams;
  const callbackUrl = params.callbackUrl ?? "/";

  return (
    <div className="flex min-h-dvh items-center justify-center px-4">
      <div className="w-full max-w-md rounded-3xl border border-white/70 bg-white/90 p-8 shadow-xl backdrop-blur">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-600">
          RelayDesk
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-slate-900">Sign up</h1>
        <SignupClient callbackUrl={callbackUrl} />
      </div>
    </div>
  );
}
