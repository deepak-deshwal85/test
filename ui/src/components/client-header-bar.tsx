"use client";

import { Label } from "@/components/ui";
import { useClientScope } from "@/contexts/client-scope-context";
import { usePermissions } from "@/hooks/use-permissions";

function ReadOnlyField({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  return (
    <div className="min-w-0">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className="truncate text-sm font-medium text-slate-900">
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
      <div className="border-b border-slate-200/80 bg-slate-50 px-4 py-3 lg:px-8">
        <p className="text-sm text-slate-500">Loading client context…</p>
      </div>
    );
  }

  if (!selectedClient && clients.length === 0) {
    return (
      <div className="border-b border-slate-200/80 bg-amber-50 px-4 py-3 lg:px-8">
        <p className="text-sm text-amber-800">
          {error ?? "No client profile available."}
        </p>
      </div>
    );
  }

  if (canManageData) {
    const email = selectedClient?.client_email_id ?? "";

    return (
      <div className="border-b border-slate-200/80 bg-slate-50 px-4 py-3 lg:px-8">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.15em] text-brand-600">
          Active client
        </p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <Label htmlFor="header_client_email">Client email</Label>
            <select
              id="header_client_email"
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
              value={email}
              onChange={(e) => selectClientByEmail(e.target.value)}
            >
              <option value="">Select email</option>
              {clients.map((client) => (
                <option key={client.id} value={client.client_email_id}>
                  {client.client_email_id}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="header_client_name">Client name</Label>
            <select
              id="header_client_name"
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
              value={email}
              onChange={(e) => selectClientByEmail(e.target.value)}
            >
              <option value="">Select name</option>
              {clients.map((client) => (
                <option key={client.id} value={client.client_email_id}>
                  {client.client_name || "(no name)"} · {client.client_email_id}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="header_client_phone">Client phone</Label>
            <select
              id="header_client_phone"
              className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
              value={email}
              onChange={(e) => selectClientByEmail(e.target.value)}
            >
              <option value="">Select phone</option>
              {clients.map((client) => (
                <option key={client.id} value={client.client_email_id}>
                  {client.client_phone_number || "(no phone)"} ·{" "}
                  {client.client_email_id}
                </option>
              ))}
            </select>
          </div>
          <ReadOnlyField
            label="Business phone"
            value={selectedClient?.client_business_phone_number}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="border-b border-slate-200/80 bg-slate-50 px-4 py-3 lg:px-8">
      <p className="mb-3 text-xs font-semibold uppercase tracking-[0.15em] text-brand-600">
        Your account
      </p>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <ReadOnlyField label="Client name" value={selectedClient?.client_name} />
        <ReadOnlyField label="Client email" value={selectedClient?.client_email_id} />
        <ReadOnlyField
          label="Client phone"
          value={selectedClient?.client_phone_number}
        />
      </div>
    </div>
  );
}
