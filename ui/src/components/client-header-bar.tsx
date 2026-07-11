"use client";

import { Label, Select, Spinner } from "@/components/ui";
import { useClientScope } from "@/contexts/client-scope-context";
import { usePermissions } from "@/hooks/use-permissions";
import { cn } from "@/lib/utils";

function MetaField({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  return (
    <div className="min-w-0">
      <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 truncate text-sm font-medium text-foreground">
        {value?.trim() ? value : "—"}
      </p>
    </div>
  );
}

export function ClientHeaderBar() {
  const { canManageData } = usePermissions();
  const {
    selectedClient,
    clients,
    loading,
    error,
    selectClientByEmail,
  } = useClientScope();

  if (loading) {
    return (
      <div className="border-b border-border bg-card px-4 py-3 sm:px-6 lg:px-8">
        <div className="mx-auto flex max-w-6xl items-center gap-2 text-sm text-muted-foreground">
          <Spinner />
          Loading client context…
        </div>
      </div>
    );
  }

  if (!selectedClient && clients.length === 0) {
    return (
      <div className="border-b border-amber-200 bg-amber-50 px-4 py-3 dark:border-amber-900/50 dark:bg-amber-950/30 sm:px-6 lg:px-8">
        <p className="mx-auto max-w-6xl text-sm text-amber-900 dark:text-amber-200">
          {error ?? "No client profile available."}
        </p>
      </div>
    );
  }

  if (canManageData) {
    const email = selectedClient?.client_email_id ?? "";

    return (
      <div className="border-b border-border bg-card px-4 py-4 sm:px-6 lg:px-8">
        <div className="mx-auto grid max-w-6xl gap-4 lg:grid-cols-[minmax(0,1.2fr)_repeat(3,minmax(0,1fr))] lg:items-end">
          <div>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-brand-600">
              Active client
            </p>
            <Label htmlFor="header_client_select" className="sr-only">
              Select client
            </Label>
            <Select
              id="header_client_select"
              value={email}
              onChange={(e) => selectClientByEmail(e.target.value)}
            >
              <option value="">Select a client…</option>
              {clients.map((client) => (
                <option key={client.id} value={client.client_email_id}>
                  {client.client_name || "(no name)"} · {client.client_email_id}
                </option>
              ))}
            </Select>
          </div>
          <MetaField label="Client name" value={selectedClient?.client_name} />
          <MetaField
            label="Personal phone"
            value={selectedClient?.client_phone_number}
          />
          <MetaField
            label="Business phone"
            value={selectedClient?.client_business_phone_number}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="border-b border-border bg-card px-4 py-4 sm:px-6 lg:px-8">
      <p className="mx-auto mb-3 max-w-6xl text-[11px] font-semibold uppercase tracking-wider text-brand-600">
        Your account
      </p>
      <div
        className={cn(
          "mx-auto grid max-w-6xl gap-4 sm:grid-cols-2",
          selectedClient?.client_business_phone_number
            ? "lg:grid-cols-4"
            : "lg:grid-cols-3",
        )}
      >
        <MetaField label="Name" value={selectedClient?.client_name} />
        <MetaField label="Email" value={selectedClient?.client_email_id} />
        <MetaField
          label="Personal phone"
          value={selectedClient?.client_phone_number}
        />
        {selectedClient?.client_business_phone_number ? (
          <MetaField
            label="Business phone"
            value={selectedClient.client_business_phone_number}
          />
        ) : null}
      </div>
    </div>
  );
}
