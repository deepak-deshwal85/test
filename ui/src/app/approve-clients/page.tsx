"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { AdminRouteGuard } from "@/components/admin-route-guard";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Input,
  PageHeader,
} from "@/components/ui";
import { apiFetch } from "@/lib/api-client";
import { useClientScope } from "@/contexts/client-scope-context";
import type { ClientAdminListResponse, ClientAdminProfile } from "@/lib/types";
import { CheckCircle2, RefreshCw } from "lucide-react";

export default function ApproveClientsPage() {
  const { refresh: refreshScope } = useClientScope();
  const [clients, setClients] = useState<ClientAdminProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [businessPhones, setBusinessPhones] = useState<Record<string, string>>(
    {},
  );
  const [approvingEmail, setApprovingEmail] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<ClientAdminListResponse>("v1/clients");
      setClients(data.clients);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load clients");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function approveClient(client: ClientAdminProfile) {
    const businessPhone = (businessPhones[client.client_email_id] ?? "").trim();
    if (!businessPhone) {
      setError("Business phone number is required to approve a client.");
      return;
    }

    setApprovingEmail(client.client_email_id);
    setError(null);
    setSuccessMessage(null);
    try {
      const updated = await apiFetch<ClientAdminProfile>("v1/clients/approve", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          client_email_id: client.client_email_id,
          client_business_phone_number: businessPhone,
        }),
      });
      setClients((current) =>
        current.map((row) =>
          row.client_email_id === updated.client_email_id ? updated : row,
        ),
      );
      setSuccessMessage(
        `Approved ${updated.client_email_id}. Ask them to sign out and sign in again.`,
      );
      await refreshScope();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval failed");
    } finally {
      setApprovingEmail(null);
    }
  }

  const pending = clients.filter((client) => !client.is_approved);
  const approved = clients.filter((client) => client.is_approved);

  return (
    <AdminRouteGuard>
      <AppShell>
        <PageHeader
          title="Approve clients"
          description="Review signed-up clients, assign a business phone, and promote them to approved-clients in Cognito."
          action={
            <Button variant="secondary" onClick={() => void load()}>
              <RefreshCw className="h-4 w-4" />
              Refresh
            </Button>
          }
        />

        {error ? <ErrorBanner message={error} /> : null}
        {successMessage ? (
          <div className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
            {successMessage}
          </div>
        ) : null}

        {loading ? (
          <p className="text-sm text-slate-500">Loading clients…</p>
        ) : clients.length === 0 ? (
          <EmptyState message="Clients appear here after they sign in via SSO for the first time." />
        ) : (
          <div className="space-y-6">
            <Card>
              <h2 className="text-base font-semibold text-slate-900">
                Pending approval ({pending.length})
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Enter a business phone number and approve to grant console access.
              </p>
              {pending.length === 0 ? (
                <p className="mt-4 text-sm text-slate-500">No pending clients.</p>
              ) : (
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 text-slate-500">
                        <th className="px-2 py-2 font-medium">Email</th>
                        <th className="px-2 py-2 font-medium">Name</th>
                        <th className="px-2 py-2 font-medium">Personal phone</th>
                        <th className="px-2 py-2 font-medium">Business phone</th>
                        <th className="px-2 py-2 font-medium">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pending.map((client) => (
                        <tr
                          key={client.id}
                          className="border-b border-slate-100 align-top"
                        >
                          <td className="px-2 py-3">{client.client_email_id}</td>
                          <td className="px-2 py-3">
                            {client.client_name || "—"}
                          </td>
                          <td className="px-2 py-3">
                            {client.client_phone_number || "—"}
                          </td>
                          <td className="px-2 py-3">
                            <Input
                              id={`business_${client.id}`}
                              aria-label="Business phone"
                              placeholder="+911171366880"
                              value={businessPhones[client.client_email_id] ?? ""}
                              onChange={(e) =>
                                setBusinessPhones((current) => ({
                                  ...current,
                                  [client.client_email_id]: e.target.value,
                                }))
                              }
                            />
                          </td>
                          <td className="px-2 py-3">
                            <Button
                              onClick={() => void approveClient(client)}
                              disabled={approvingEmail === client.client_email_id}
                            >
                              <CheckCircle2 className="h-4 w-4" />
                              {approvingEmail === client.client_email_id
                                ? "Approving…"
                                : "Approve"}
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

            <Card>
              <h2 className="text-base font-semibold text-slate-900">
                Approved ({approved.length})
              </h2>
              {approved.length === 0 ? (
                <p className="mt-4 text-sm text-slate-500">No approved clients yet.</p>
              ) : (
                <div className="mt-4 overflow-x-auto">
                  <table className="min-w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 text-slate-500">
                        <th className="px-2 py-2 font-medium">Email</th>
                        <th className="px-2 py-2 font-medium">Name</th>
                        <th className="px-2 py-2 font-medium">Personal phone</th>
                        <th className="px-2 py-2 font-medium">Business phone</th>
                        <th className="px-2 py-2 font-medium">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {approved.map((client) => (
                        <tr
                          key={client.id}
                          className="border-b border-slate-100"
                        >
                          <td className="px-2 py-3">{client.client_email_id}</td>
                          <td className="px-2 py-3">
                            {client.client_name || "—"}
                          </td>
                          <td className="px-2 py-3">
                            {client.client_phone_number || "—"}
                          </td>
                          <td className="px-2 py-3">
                            {client.client_business_phone_number || "—"}
                          </td>
                          <td className="px-2 py-3">
                            <Badge className="bg-emerald-100 text-emerald-800">
                              Approved
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
        )}
      </AppShell>
    </AdminRouteGuard>
  );
}
