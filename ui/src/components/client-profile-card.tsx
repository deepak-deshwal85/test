"use client";

import { useState } from "react";
import { Button, Card, ErrorBanner, Input, Label } from "@/components/ui";
import { apiFetch } from "@/lib/api-client";
import type { ClientProfile } from "@/lib/types";
import { usePermissions } from "@/hooks/use-permissions";

type ClientProfileCardProps = {
  profile: ClientProfile | null;
  loading: boolean;
  onUpdated: () => Promise<void>;
};

export function ClientProfileCard({
  profile,
  loading,
  onUpdated,
}: ClientProfileCardProps) {
  const { canManageData } = usePermissions();
  const [name, setName] = useState("");
  const [personalPhone, setPersonalPhone] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);

  function startEdit() {
    setName(profile?.client_name ?? "");
    setPersonalPhone(profile?.client_phone_number ?? "");
    setEditing(true);
    setError(null);
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await apiFetch<ClientProfile>("v1/clients/profile", {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          client_name: name,
          client_phone_number: personalPhone || null,
        }),
      });
      setEditing(false);
      await onUpdated();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save profile");
    } finally {
      setSaving(false);
    }
  }

  if (canManageData) return null;

  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-semibold text-slate-900">Your profile</h2>
          <p className="mt-1 text-sm text-slate-600">
            Email and business phone are managed by RelayDesk. You can update your
            name and personal phone number.
          </p>
        </div>
        {!editing ? (
          <Button variant="secondary" onClick={startEdit} disabled={loading}>
            Edit
          </Button>
        ) : null}
      </div>

      {error ? <div className="mt-4"><ErrorBanner message={error} /></div> : null}

      {loading ? (
        <p className="mt-4 text-sm text-slate-500">Loading profile…</p>
      ) : editing ? (
        <form className="mt-4 space-y-3" onSubmit={handleSave}>
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
              value={profile?.client_email_id ?? ""}
              disabled
            />
          </div>
          <div>
            <Label htmlFor="profile_business_phone">Business phone</Label>
            <Input
              id="profile_business_phone"
              value={profile?.client_business_phone_number ?? ""}
              disabled
            />
          </div>
          <div className="flex gap-2">
            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => setEditing(false)}
            >
              Cancel
            </Button>
          </div>
        </form>
      ) : (
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-slate-500">Name</dt>
            <dd className="font-medium text-slate-900">
              {profile?.client_name || "—"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Email</dt>
            <dd className="font-medium text-slate-900">
              {profile?.client_email_id ?? "—"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Personal phone</dt>
            <dd className="font-medium text-slate-900">
              {profile?.client_phone_number || "—"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Business phone</dt>
            <dd className="font-medium text-slate-900">
              {profile?.client_business_phone_number || "—"}
            </dd>
          </div>
        </dl>
      )}
    </Card>
  );
}
