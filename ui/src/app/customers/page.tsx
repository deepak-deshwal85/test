"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import {
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Input,
  Label,
  PageHeader,
} from "@/components/ui";
import { apiFetch } from "@/lib/api-client";
import { clientScopeQuery, useClientScope } from "@/contexts/client-scope-context";
import { usePermissions } from "@/hooks/use-permissions";
import type { Customer, CustomerListResponse } from "@/lib/types";
import { Pencil, Plus, Trash2 } from "lucide-react";

const emptyConsumerForm = {
  consumer_phone_number: "",
  consumer_email_id: "",
};

export default function CustomersPage() {
  const { canManageData, canManageOwnCustomers } = usePermissions();
  const { selectedClient, clientEmailId, ready } = useClientScope();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(emptyConsumerForm);
  const [editingId, setEditingId] = useState<number | null>(null);

  const canEditCustomers = canManageData || canManageOwnCustomers;

  async function load() {
    if (!ready || !clientEmailId) {
      setCustomers([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const query = `v1/customers?client_email_id=${encodeURIComponent(clientEmailId)}`;
      const data = await apiFetch<CustomerListResponse>(query);
      setCustomers(data.customers);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load customers");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [clientEmailId, ready]);

  function buildCreatePayload() {
    if (!selectedClient?.client_business_phone_number) {
      throw new Error("Selected client has no business phone configured.");
    }
    return {
      client_business_phone_number: selectedClient.client_business_phone_number,
      client_name: selectedClient.client_name || "Client",
      client_email_id: selectedClient.client_email_id,
      consumer_phone_number: form.consumer_phone_number,
      consumer_email_id: form.consumer_email_id,
    };
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!clientEmailId) return;
    setError(null);
    try {
      const scope = clientScopeQuery(clientEmailId);
      if (editingId) {
        await apiFetch(`v1/customers/${editingId}?${scope}`, {
          method: "PUT",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            consumer_phone_number: form.consumer_phone_number,
            consumer_email_id: form.consumer_email_id,
          }),
        });
      } else {
        await apiFetch("v1/customers", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(buildCreatePayload()),
        });
      }
      setForm(emptyConsumerForm);
      setEditingId(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  }

  async function handleDelete(id: number) {
    if (!clientEmailId || !confirm("Delete this customer?")) return;
    try {
      const scope = clientScopeQuery(clientEmailId);
      await apiFetch(`v1/customers/${id}?${scope}`, { method: "DELETE" });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  function startEdit(customer: Customer) {
    setEditingId(customer.id);
    setForm({
      consumer_phone_number: customer.consumer_phone_number,
      consumer_email_id: customer.consumer_email_id,
    });
  }

  async function handleApprove(customer: Customer) {
    try {
      await apiFetch(
        `v1/customers/${customer.id}/approve?client_email_id=${encodeURIComponent(customer.client_email_id)}`,
        { method: "POST" },
      );
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Approve failed");
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Customers"
        description="Manage consumers for the selected client."
        action={
          <Button onClick={() => void load()} variant="secondary">
            Refresh
          </Button>
        }
      />

      {error ? <ErrorBanner message={error} /> : null}

      {!clientEmailId ? (
        <EmptyState message="Select a client in the header to view customers." />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
          {canEditCustomers ? (
            <Card>
              <h2 className="font-semibold text-slate-900">
                {editingId ? "Edit consumer" : "Add consumer"}
              </h2>
              <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
                <div>
                  <Label htmlFor="consumer_phone">Consumer phone</Label>
                  <Input
                    id="consumer_phone"
                    required
                    value={form.consumer_phone_number}
                    onChange={(e) =>
                      setForm({ ...form, consumer_phone_number: e.target.value })
                    }
                  />
                </div>
                <div>
                  <Label htmlFor="consumer_email">Consumer email</Label>
                  <Input
                    id="consumer_email"
                    required
                    value={form.consumer_email_id}
                    onChange={(e) =>
                      setForm({ ...form, consumer_email_id: e.target.value })
                    }
                  />
                </div>
                <div className="flex gap-2">
                  <Button type="submit">
                    <Plus className="h-4 w-4" />
                    {editingId ? "Update" : "Create"}
                  </Button>
                  {editingId ? (
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => {
                        setEditingId(null);
                        setForm(emptyConsumerForm);
                      }}
                    >
                      Cancel
                    </Button>
                  ) : null}
                </div>
              </form>
            </Card>
          ) : (
            <Card>
              <h2 className="font-semibold text-slate-900">Read-only access</h2>
              <p className="mt-2 text-sm text-slate-600">
                Your role can view customers but cannot create or edit records.
              </p>
            </Card>
          )}

          <Card>
            {loading ? (
              <p className="text-sm text-slate-500">Loading…</p>
            ) : customers.length === 0 ? (
              <EmptyState message="No customers for this client yet." />
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="text-slate-500">
                    <tr>
                      <th className="px-2 py-2">Consumer phone</th>
                      <th className="px-2 py-2">Consumer email</th>
                      <th className="px-2 py-2">Status</th>
                      {canEditCustomers ? (
                        <th className="px-2 py-2">Actions</th>
                      ) : null}
                    </tr>
                  </thead>
                  <tbody>
                    {customers.map((customer) => (
                      <tr key={customer.id} className="border-t border-slate-100">
                        <td className="px-2 py-3">
                          {customer.consumer_phone_number}
                        </td>
                        <td className="px-2 py-3">
                          {customer.consumer_email_id}
                        </td>
                        <td className="px-2 py-3">
                          {customer.is_approved ? "approved" : "pending"}
                        </td>
                        {canEditCustomers ? (
                          <td className="px-2 py-3">
                            <div className="flex gap-2">
                              <Button
                                variant="ghost"
                                onClick={() => startEdit(customer)}
                              >
                                <Pencil className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                onClick={() => void handleDelete(customer.id)}
                              >
                                <Trash2 className="h-4 w-4 text-red-600" />
                              </Button>
                              {canManageData && !customer.is_approved ? (
                                <Button
                                  variant="secondary"
                                  onClick={() => void handleApprove(customer)}
                                >
                                  Approve
                                </Button>
                              ) : null}
                            </div>
                          </td>
                        ) : null}
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
  );
}
