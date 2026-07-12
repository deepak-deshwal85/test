"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { AppShell } from "@/components/app-shell";
import { DeleteClientAccountSection } from "@/components/delete-client-account-section";
import { ThemeToggle } from "@/components/theme-toggle";
import {
  Button,
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
  ErrorBanner,
  Input,
  Label,
  PageHeader,
  Spinner,
  SuccessBanner,
} from "@/components/ui";
import { PhoneInput } from "@/components/phone-input";
import { apiFetch } from "@/lib/api-client";
import { useClientScope } from "@/contexts/client-scope-context";
import { usePermissions } from "@/hooks/use-permissions";
import { roleLabel } from "@/lib/roles";
import {
  combineOptionalPhoneParts,
  EMPTY_PHONE_FIELDS,
  formatPhoneDisplay,
  splitStoredPhone,
  type PhoneFields,
} from "@/lib/phone";
import type { ClientProfile } from "@/lib/types";

function AppearanceCard() {
  return (
    <Card className="max-w-lg">
      <CardHeader>
        <CardTitle>Appearance</CardTitle>
        <CardDescription>
          Choose light, dark, or match your system preference.
        </CardDescription>
      </CardHeader>
      <ThemeToggle />
    </Card>
  );
}

function AdminAccountCard() {
  const { data: session } = useSession();
  const { role } = usePermissions();
  const userRole = role ?? "guest-clients";

  return (
    <Card className="max-w-lg">
      <CardHeader>
        <CardTitle>Account</CardTitle>
        <CardDescription>
          Your signed-in admin identity. Client data is managed via the header
          selector on other pages.
        </CardDescription>
      </CardHeader>
      <dl className="space-y-4 text-sm">
        <div>
          <dt className="font-medium text-muted-foreground">Name</dt>
          <dd className="mt-1 text-foreground">
            {session?.user?.name ?? "—"}
          </dd>
        </div>
        <div>
          <dt className="font-medium text-muted-foreground">Email</dt>
          <dd className="mt-1 text-foreground">
            {session?.user?.email ?? "—"}
          </dd>
        </div>
        <div>
          <dt className="font-medium text-muted-foreground">Role</dt>
          <dd className="mt-1 text-foreground">{roleLabel(userRole)}</dd>
        </div>
      </dl>
    </Card>
  );
}

function ClientProfileForm() {
  const { selectedClient, loading, refresh } = useClientScope();
  const [name, setName] = useState("");
  const [personalPhone, setPersonalPhone] = useState<PhoneFields>({
    ...EMPTY_PHONE_FIELDS,
  });
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (selectedClient) {
      setName(selectedClient.client_name);
      setPersonalPhone(splitStoredPhone(selectedClient.client_phone_number));
    }
  }, [selectedClient]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setPhoneError(null);
    setSuccess(null);
    let storedPhone: string | null;
    try {
      storedPhone = combineOptionalPhoneParts(personalPhone);
    } catch (e) {
      setPhoneError(e instanceof Error ? e.message : "Invalid phone number");
      setSaving(false);
      return;
    }
    try {
      await apiFetch<ClientProfile>("v1/clients/profile", {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          client_name: name,
          client_phone_number: storedPhone,
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

  return (
    <>
      {error ? <ErrorBanner message={error} /> : null}
      {success ? <SuccessBanner message={success} /> : null}

      <Card className="max-w-lg">
        <CardHeader>
          <CardTitle>Personal information</CardTitle>
          <CardDescription>
            Update your name and personal phone. Email and business phone are
            managed by RelayDesk.
          </CardDescription>
        </CardHeader>
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner />
            Loading profile…
          </div>
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
              <PhoneInput
                label="Personal phone"
                countryCodeId="profile_country_code"
                nationalNumberId="profile_personal_phone"
                value={personalPhone}
                error={phoneError}
                hint="Optional. Stored as digits only without + sign."
                onChange={(value) => {
                  setPhoneError(null);
                  setPersonalPhone(value);
                }}
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
                value={
                  selectedClient?.client_business_phone_number
                    ? formatPhoneDisplay(selectedClient.client_business_phone_number)
                    : ""
                }
                disabled
              />
            </div>
            <Button type="submit" disabled={saving}>
              {saving ? <Spinner /> : null}
              {saving ? "Saving…" : "Save changes"}
            </Button>
          </form>
        )}
      </Card>
    </>
  );
}

export default function ProfilePage() {
  const { canManageData } = usePermissions();
  const { clients, selectedClient, refresh } = useClientScope();

  return (
    <AppShell>
      <PageHeader
        title="Profile"
        description={
          canManageData
            ? "Account settings, client deletion, and appearance preferences."
            : "Update your personal information and appearance preferences."
        }
      />

      <div className="space-y-6">
        {canManageData ? <AdminAccountCard /> : <ClientProfileForm />}
        {canManageData ? (
          <DeleteClientAccountSection
            clients={clients}
            defaultEmail={selectedClient?.client_email_id}
            onDeleted={async () => {
              await refresh();
            }}
          />
        ) : null}
        <AppearanceCard />
      </div>
    </AppShell>
  );
}
