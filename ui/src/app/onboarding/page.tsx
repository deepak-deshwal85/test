"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  Button,
  Card,
  ErrorBanner,
  Input,
  Label,
  PageHeader,
} from "@/components/ui";
import { apiFetch } from "@/lib/api-client";
import { useClientProfile } from "@/hooks/use-client-profile";
import type { ClientProfile } from "@/lib/types";

export default function OnboardingPage() {
  const router = useRouter();
  const { data: session } = useSession();
  const { refresh } = useClientProfile();
  const email = session?.user?.email ?? "";
  const [clientName, setClientName] = useState(session?.user?.name ?? "");
  const [clientPhone, setClientPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email) {
      setError("Your account email is missing from the session.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await apiFetch<ClientProfile>("v1/clients/profile", {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          client_name: clientName.trim(),
          client_phone_number: clientPhone.trim(),
          client_email_id: email.toLowerCase(),
        }),
      });
      await refresh();
      router.replace("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save profile");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex min-h-dvh items-center justify-center px-4">
      <Card className="w-full max-w-lg">
        <PageHeader
          title="Complete authorization"
          description="Provide your name and business phone number to access your knowledge base and customer data."
        />
        {error ? <ErrorBanner message={error} /> : null}
        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <div>
            <Label htmlFor="email">Email</Label>
            <Input id="email" value={email} disabled />
          </div>
          <div>
            <Label htmlFor="name">Your name</Label>
            <Input
              id="name"
              required
              placeholder="Jane Smith"
              value={clientName}
              onChange={(e) => setClientName(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="phone">Business phone number</Label>
            <Input
              id="phone"
              required
              placeholder="911171366880"
              value={clientPhone}
              onChange={(e) => setClientPhone(e.target.value)}
            />
            <p className="mt-1 text-xs text-slate-500">
              Used for your RAG collection (phone_&lt;digits&gt;).
            </p>
          </div>
          <Button type="submit" disabled={saving}>
            {saving ? "Saving…" : "Continue"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
