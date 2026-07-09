"use client";

import { signOut } from "next-auth/react";
import { LogOut } from "lucide-react";
import { Button } from "@/components/ui";

export function GuestOnboardingGate() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <div className="max-w-lg rounded-3xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-600">
          RelayDesk
        </p>
        <h1 className="mt-3 text-2xl font-semibold text-slate-900">
          Onboarding required
        </h1>
        <p className="mt-4 text-sm leading-relaxed text-slate-600">
          Your account is not onboarded yet. Please contact the product owner to
          complete onboarding and get access to the console.
        </p>
        <Button
          className="mt-6"
          variant="secondary"
          onClick={() => signOut({ callbackUrl: "/login" })}
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </Button>
      </div>
    </div>
  );
}
