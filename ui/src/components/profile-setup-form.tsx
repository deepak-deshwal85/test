"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { Button, ErrorBanner, Input, Label } from "@/components/ui";
import { apiFetch } from "@/lib/api-client";
import type { ClientProfile } from "@/lib/types";

export function ProfileSetupForm({
  onComplete,
}: {
  onComplete?: () => void | Promise<void>;
}) {
  const router = useRouter();
  const { data: session, update } = useSession();
  const email = session?.user?.email ?? "";
  const [clientName, setClientName] = useState(session?.user?.name ?? "");
  const [clientPhone, setClientPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email) {
      setError("Email missing from session. Sign out and sign in again.");
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
      await update();
      if (onComplete) {
        await onComplete();
      } else {
        router.replace("/");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save profile");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
      {error ? <ErrorBanner message={error} /> : null}
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
      </div>
      <Button type="submit" className="w-full" disabled={saving || !email}>
        {saving ? "Saving…" : "Save and continue"}
      </Button>
    </form>
  );
}
