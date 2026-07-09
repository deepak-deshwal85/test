"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import {
  Button,
  Card,
  ErrorBanner,
  Input,
  Label,
  PageHeader,
} from "@/components/ui";
import { apiFetch } from "@/lib/api-client";
import { useClientScope } from "@/contexts/client-scope-context";
import { usePermissions } from "@/hooks/use-permissions";
import type { ClientProfile } from "@/lib/types";
import { useRouter } from "next/navigation";

export default function ProfilePage() {
  const router = useRouter();
  const { canManageData } = usePermissions();
  const { selectedClient, loading, refresh } = useClientScope();
  const [name, setName] = useState("");
  const [personalPhone, setPersonalPhone] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (canManageData) {
      router.replace("/");
    }
  }, [canManageData, router]);

  useEffect(() => {
    if (selectedClient) {
      setName(selectedClient.client_name);
      setPersonalPhone(selectedClient.client_phone_number ?? "");
    }
  }, [selectedClient]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await apiFetch<ClientProfile>("v1/clients/profile", {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          client_name: name,
          client_phone_number: personalPhone || null,
        }),
      });
      await refresh();
      setSuccess("Personal information updated.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save profile");
    } finally {
      setSaving(false);
    }
  }

  if (canManageData) return null;

  return (
    <AppShell>
      <PageHeader
        title="Personal information"
        description="Update your name and personal phone number. Email and business phone are managed by RelayDesk."
      />

      {error ? <ErrorBanner message={error} /> : null}
      {success ? (
        <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {success}
        </div>
      ) : null}

      <Card className="max-w-lg">
        {loading ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : (
          <form className="space-y-4" onSubmit={handleSave}>
            <div>
              <Label htmlFor="profile_name">Name</Label>
              <Input
                id="profile_name"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="profile_personal_phone">Personal phone</Label>
              <Input
                id="profile_personal_phone"
                value={personalPhone}
                onChange={(e) => setPersonalPhone(e.target.value)}
                placeholder="+91..."
              />
            </div>
            <div>
              <Label htmlFor="profile_email">Email</Label>
              <Input
                id="profile_email"
                value={selectedClient?.client_email_id ?? ""}
                disabled
              />
            </div>
            <div>
              <Label htmlFor="profile_business_phone">Business phone</Label>
              <Input
                id="profile_business_phone"
                value={selectedClient?.client_business_phone_number ?? ""}
                disabled
              />
            </div>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save changes"}
            </Button>
          </form>
        )}
      </Card>
    </AppShell>
  );
}
