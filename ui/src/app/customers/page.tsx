"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { ClientProfileCard } from "@/components/client-profile-card";
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
import { clientScopeQuery, useClientProfile } from "@/hooks/use-client-profile";
import { usePermissions } from "@/hooks/use-permissions";
import type { Customer, CustomerListResponse } from "@/lib/types";
import { Pencil, Plus, Trash2 } from "lucide-react";

export default function CustomersPage() {
  const { canManageData, canManageOwnCustomers } = usePermissions();
  const {
    clientEmailId,
    profile,
    loading: profileLoading,
    refresh: refreshProfile,
    ready,
  } = useClientProfile();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    client_business_phone_number: "",
    client_name: "",
    client_email_id: "",
    consumer_phone_number: "",
    consumer_email_id: "",
  });
  const [editingId, setEditingId] = useState<number | null>(null);

  const scopedEmail = canManageData ? filter : (clientEmailId ?? "");
  const canEditCustomers = canManageData || canManageOwnCustomers;

  useEffect(() => {
    if (!canManageData && clientEmailId) {
      setFilter(clientEmailId);
    }
  }, [canManageData, clientEmailId]);

  useEffect(() => {
    if (!canManageData && profile) {
      setForm((current) => ({
        ...current,
        client_business_phone_number: profile.client_business_phone_number ?? "",
        client_name: profile.client_name,
        client_email_id: profile.client_email_id,
      }));
    }
  }, [canManageData, profile]);

  async function load() {
    if (!canManageData && !ready) return;
    setLoading(true);
    setError(null);
    try {
      if (!scopedEmail) {
        setCustomers([]);
        return;
      }
      const query = `v1/customers?client_email_id=${encodeURIComponent(scopedEmail)}`;
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
  }, [scopedEmail, ready]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const scope = clientScopeQuery(scopedEmail);
      if (editingId) {
        const payload = canManageData
          ? form
          : {
              client_name: form.client_name,
              consumer_phone_number: form.consumer_phone_number,
              consumer_email_id: form.consumer_email_id,
            };
        await apiFetch(`v1/customers/${editingId}?${scope}`, {
          method: "PUT",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(payload),
        });
      } else {
        await apiFetch("v1/customers", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(form),
        });
      }
      setForm({
        client_business_phone_number:
          profile?.client_business_phone_number ?? form.client_business_phone_number,
        client_name: profile?.client_name ?? form.client_name,
        client_email_id: profile?.client_email_id ?? form.client_email_id,
        consumer_phone_number: "",
        consumer_email_id: "",
      });
      setEditingId(null);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Delete this customer?")) return;
    try {
      const scope = clientScopeQuery(scopedEmail);
      await apiFetch(`v1/customers/${id}?${scope}`, { method: "DELETE" });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  function startEdit(customer: Customer) {
    setEditingId(customer.id);
    setForm({
      client_business_phone_number: customer.client_business_phone_number,
      client_name: customer.client_name,
      client_email_id: customer.client_email_id,
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
        description="Manage client consumers for outbound voice campaigns."
        action={
          <Button onClick={() => void load()} variant="secondary">
            Refresh
          </Button>
        }
      />

      {error ? <ErrorBanner message={error} /> : null}

      {!canManageData ? (
        <div className="mb-6">
          <ClientProfileCard
            profile={profile}
            loading={profileLoading}
            onUpdated={refreshProfile}
          />
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
        {canEditCustomers ? (
          <Card>
            <h2 className="font-semibold text-slate-900">
              {editingId ? "Edit customer" : "Add customer"}
            </h2>
            <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
              {canManageData ? (
                <>
                  <div>
                    <Label htmlFor="client_business_phone">
                      Client business phone
                    </Label>
                    <Input
                      id="client_business_phone"
                      required
                      value={form.client_business_phone_number}
                      onChange={(e) =>
                        setForm({
                          ...form,
                          client_business_phone_number: e.target.value,
                        })
                      }
                    />
                  </div>
                  <div>
                    <Label htmlFor="client_name">Client name</Label>
                    <Input
                      id="client_name"
                      required
                      value={form.client_name}
                      onChange={(e) =>
                        setForm({ ...form, client_name: e.target.value })
                      }
                    />
                  </div>
                  <div>
                    <Label htmlFor="client_email">Client email</Label>
                    <Input
                      id="client_email"
                      required
                      value={form.client_email_id}
                      onChange={(e) =>
                        setForm({ ...form, client_email_id: e.target.value })
                      }
                    />
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <Label>Business phone</Label>
                    <Input
                      value={form.client_business_phone_number}
                      disabled
                    />
                  </div>
                  <div>
                    <Label>Email</Label>
                    <Input value={form.client_email_id} disabled />
                  </div>
                </>
              )}
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
                      setForm({
                        client_business_phone_number:
                          profile?.client_business_phone_number ?? "",
                        client_name: profile?.client_name ?? "",
                        client_email_id: profile?.client_email_id ?? "",
                        consumer_phone_number: "",
                        consumer_email_id: "",
                      });
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
          {canManageData ? (
            <div className="mb-4 flex flex-col gap-3 sm:flex-row">
              <Input
                placeholder="Filter by client email"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              />
              <Button variant="secondary" onClick={() => void load()}>
                Apply filter
              </Button>
            </div>
          ) : null}

          {loading ? (
            <p className="text-sm text-slate-500">Loading…</p>
          ) : customers.length === 0 ? (
            <EmptyState message="No customers found." />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="text-slate-500">
                  <tr>
                    <th className="px-2 py-2">Client</th>
                    <th className="px-2 py-2">Consumer</th>
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
                        <p className="font-medium">{customer.client_name}</p>
                        <p className="text-slate-500">
                          {customer.client_business_phone_number}
                        </p>
                        <p className="text-slate-500">{customer.client_email_id}</p>
                      </td>
                      <td className="px-2 py-3">
                        <div>{customer.consumer_phone_number}</div>
                        <div className="text-slate-500">
                          {customer.consumer_email_id}
                        </div>
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
    </AppShell>
  );
}
