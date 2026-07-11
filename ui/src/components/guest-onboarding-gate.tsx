"use client";

import { signOut } from "next-auth/react";
import { LogOut, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui";

export function GuestOnboardingGate() {
  return (
    <div className="flex min-h-[calc(100dvh-3.5rem)] items-center justify-center px-4 py-12">
      <div className="w-full max-w-md rounded-xl border border-zinc-200 bg-white p-8 text-center shadow-[var(--shadow-card)]">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-amber-50 text-amber-600">
          <ShieldAlert className="h-6 w-6" aria-hidden />
        </div>
        <h1 className="mt-5 text-xl font-semibold tracking-tight text-zinc-900">
          Onboarding required
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-zinc-500">
          Your account is not onboarded yet. Contact the product owner to complete
          onboarding and get access to the console.
        </p>
        <Button
          className="mt-6 w-full sm:w-auto"
          variant="secondary"
          onClick={() => signOut({ callbackUrl: "/login" })}
        >
          <LogOut className="h-4 w-4" aria-hidden />
          Sign out
        </Button>
      </div>
    </div>
  );
}
