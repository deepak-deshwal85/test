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
import type { Customer, CustomerListResponse } from "@/lib/types";
import { Pencil, Plus, Trash2 } from "lucide-react";

export default function CustomersPage() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    client_phone_number: "",
    client_name: "",
    consumer_phone_number: "",
  });
  const [editingId, setEditingId] = useState<number | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const query = filter
        ? `v1/customers?client_phone_number=${encodeURIComponent(filter)}`
        : "v1/customers";
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
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      if (editingId) {
        await apiFetch(`v1/customers/${editingId}`, {
          method: "PUT",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(form),
        });
      } else {
        await apiFetch("v1/customers", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(form),
        });
      }
      setForm({
        client_phone_number: "",
        client_name: "",
        consumer_phone_number: "",
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
      await apiFetch(`v1/customers/${id}`, { method: "DELETE" });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  function startEdit(customer: Customer) {
    setEditingId(customer.id);
    setForm({
      client_phone_number: customer.client_phone_number,
      client_name: customer.client_name,
      consumer_phone_number: customer.consumer_phone_number,
    });
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

      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
        <Card>
          <h2 className="font-semibold text-slate-900">
            {editingId ? "Edit customer" : "Add customer"}
          </h2>
          <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
            <div>
              <Label htmlFor="client_phone">Client phone</Label>
              <Input
                id="client_phone"
                required
                value={form.client_phone_number}
                onChange={(e) =>
                  setForm({ ...form, client_phone_number: e.target.value })
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
                      client_phone_number: "",
                      client_name: "",
                      consumer_phone_number: "",
                    });
                  }}
                >
                  Cancel
                </Button>
              ) : null}
            </div>
          </form>
        </Card>

        <Card>
          <div className="mb-4 flex flex-col gap-3 sm:flex-row">
            <Input
              placeholder="Filter by client phone"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
            <Button variant="secondary" onClick={() => void load()}>
              Apply filter
            </Button>
          </div>

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
                    <th className="px-2 py-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {customers.map((customer) => (
                    <tr key={customer.id} className="border-t border-slate-100">
                      <td className="px-2 py-3">
                        <p className="font-medium">{customer.client_name}</p>
                        <p className="text-slate-500">
                          {customer.client_phone_number}
                        </p>
                      </td>
                      <td className="px-2 py-3">
                        {customer.consumer_phone_number}
                      </td>
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
                        </div>
                      </td>
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
