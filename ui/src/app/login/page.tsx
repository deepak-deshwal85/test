import { LoginBrand, LoginClient } from "@/components/login-client";
import { ThemeToggle } from "@/components/theme-toggle";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ callbackUrl?: string; error?: string }>;
}) {
  const params = await searchParams;
  const callbackUrl = params.callbackUrl ?? "/";
  const useCognito = Boolean(process.env.COGNITO_ISSUER);

  return (
    <div className="min-h-dvh bg-background">
      <div className="mx-auto grid min-h-dvh max-w-6xl lg:grid-cols-2">
        <section className="hidden flex-col justify-between border-r border-border bg-card p-10 lg:flex">
          <LoginBrand />
          <div className="max-w-md">
            <h2 className="text-3xl font-semibold tracking-tight text-foreground">
              Run voice campaigns with clarity
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              Manage customers, knowledge bases, outbound call jobs, and client
              approvals from one operations console.
            </p>
          </div>
          <p className="text-xs text-muted-foreground">© RelayDesk</p>
        </section>

        <section className="flex items-center justify-center px-4 py-12 sm:px-8">
          <div className="w-full max-w-md">
            <div className="mb-8 flex items-center justify-between lg:hidden">
              <LoginBrand />
              <ThemeToggle compact />
            </div>
            <div className="rounded-xl border border-border bg-card p-8 shadow-[var(--shadow-card)]">
              <div className="mb-6 hidden items-center justify-end lg:flex">
                <ThemeToggle compact />
              </div>
              <h1 className="text-2xl font-semibold tracking-tight text-foreground">
                Sign in
              </h1>
              <LoginClient
                callbackUrl={callbackUrl}
                useCognito={useCognito}
                authError={params.error}
              />
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
