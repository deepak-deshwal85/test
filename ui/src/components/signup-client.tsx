"use client";

import Link from "next/link";
import { signIn, useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ProfileSetupForm } from "@/components/profile-setup-form";
import { Button, ErrorBanner, Input, Label } from "@/components/ui";
import { useClientProfile } from "@/hooks/use-client-profile";
import {
  clearPendingProfile,
  readPendingProfile,
  writePendingProfile,
} from "@/lib/pending-profile";
import { isAuthDisabledForLocal } from "@/lib/runtime-config";

export function SignupClient({ callbackUrl }: { callbackUrl: string }) {
  const router = useRouter();
  const { status } = useSession();
  const { needsOnboarding, loading: profileLoading, applyProfile } =
    useClientProfile();
  const skipSsoInLocal = isAuthDisabledForLocal();
  const pending = readPendingProfile();

  const [clientName, setClientName] = useState("");
  const [clientPhone, setClientPhone] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  if (status === "loading" || (status === "authenticated" && profileLoading)) {
    return <p className="mt-8 text-sm text-slate-500">Loading…</p>;
  }

  if (status === "authenticated" && !needsOnboarding) {
    router.replace(callbackUrl);
    return null;
  }

  if (status === "authenticated" && needsOnboarding) {
    return (
      <>
        <p className="mt-2 text-sm text-slate-600">
          Confirm your details to finish creating your account.
        </p>
        <ProfileSetupForm
          initialName={pending?.clientName}
          initialPhone={pending?.clientPhone}
          onComplete={(profile) => {
            clearPendingProfile();
            applyProfile(profile);
            router.replace(callbackUrl);
          }}
        />
      </>
    );
  }

  function startSignup() {
    const name = clientName.trim();
    const phone = clientPhone.trim();
    if (!name || !phone) {
      setFormError("Name and business phone are required.");
      return;
    }
    setFormError(null);
    writePendingProfile({ clientName: name, clientPhone: phone });
    if (skipSsoInLocal) {
      void signIn("credentials", { callbackUrl: "/signup" });
      return;
    }
    void signIn("cognito", { callbackUrl: "/signup" });
  }

  return (
    <>
      <p className="mt-2 text-sm text-slate-600">
        Enter your name and business phone, then continue with SSO. Your email
        will be linked from your sign-in provider.
      </p>

      {formError ? (
        <div className="mt-6">
          <ErrorBanner message={formError} />
        </div>
      ) : null}

      <form
        className="mt-6 space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          startSignup();
        }}
      >
        <div>
          <Label htmlFor="signup-name">Your name</Label>
          <Input
            id="signup-name"
            required
            placeholder="Jane Smith"
            value={clientName}
            onChange={(e) => setClientName(e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="signup-phone">Business phone number</Label>
          <Input
            id="signup-phone"
            required
            placeholder="911171366880"
            value={clientPhone}
            onChange={(e) => setClientPhone(e.target.value)}
          />
        </div>
        <Button type="submit" className="w-full">
          {skipSsoInLocal ? "Continue in local mode" : "Continue with SSO"}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-slate-600">
        Already have an account?{" "}
        <Link href="/login" className="font-medium text-brand-600 hover:underline">
          Sign in
        </Link>
      </p>
    </>
  );
}
