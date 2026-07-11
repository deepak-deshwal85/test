"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { CustomerCallHistorySheet } from "@/components/customer-call-history-sheet";
import {
  Button,
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorBanner,
  Input,
  Label,
  PageHeader,
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  Spinner,
  SplitLayout,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "@/components/ui";
import { apiFetch } from "@/lib/api-client";
import { clientScopeQuery, useClientScope } from "@/contexts/client-scope-context";
import { usePermissions } from "@/hooks/use-permissions";
import type { Customer, CustomerListResponse } from "@/lib/types";
import { Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";

const emptyConsumerForm = {
  consumer_phone_number: "",
  consumer_email_id: "",
};

function normalizePhoneInput(value: string): string {
  return value.replace(/\D/g, "");
}

export default function CustomersPage() {
  const searchParams = useSearchParams();
  const { canManageData, canManageOwnCustomers } = usePermissions();
  const { selectedClient, clientEmailId, ready } = useClientScope();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(emptyConsumerForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [mobileFormOpen, setMobileFormOpen] = useState(false);
  const [historyCustomer, setHistoryCustomer] = useState<Customer | null>(null);

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

  useEffect(() => {
    const customerParam = searchParams.get("customer");
    if (!customerParam || customers.length === 0) {
      return;
    }
    const customerId = Number(customerParam);
    if (!Number.isFinite(customerId)) {
      return;
    }
    const match = customers.find((customer) => customer.id === customerId);
    if (match) {
      setHistoryCustomer(match);
    }
  }, [customers, searchParams]);

  function buildCreatePayload() {
    if (!selectedClient?.client_business_phone_number) {
      throw new Error("Selected client has no business phone configured.");
    }
    return {
      client_business_phone_number: selectedClient.client_business_phone_number,
      client_name: selectedClient.client_name || "Client",
      client_email_id: selectedClient.client_email_id,
      consumer_phone_number: normalizePhoneInput(form.consumer_phone_number),
      consumer_email_id: form.consumer_email_id.trim().toLowerCase(),
    };
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!clientEmailId || saving) return;
    setError(null);
    setSaving(true);
    try {
      const scope = clientScopeQuery(clientEmailId);
      const consumerPhone = normalizePhoneInput(form.consumer_phone_number);
      const consumerEmail = form.consumer_email_id.trim().toLowerCase();
      if (!consumerPhone) {
        throw new Error("Consumer phone number is required.");
      }
      if (!consumerEmail) {
        throw new Error("Consumer email is required.");
      }
      if (editingId) {
        await apiFetch(`v1/customers/${editingId}?${scope}`, {
          method: "PUT",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            consumer_phone_number: consumerPhone,
            consumer_email_id: consumerEmail,
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
      setMobileFormOpen(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
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
    setMobileFormOpen(true);
  }

  function resetForm() {
    setEditingId(null);
    setForm(emptyConsumerForm);
    setMobileFormOpen(false);
  }

  const consumerForm = (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <div>
        <Label htmlFor="consumer_phone">Consumer phone</Label>
        <Input
          id="consumer_phone"
          required
          inputMode="tel"
          autoComplete="tel"
          placeholder="9876543210"
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
          type="email"
          autoComplete="email"
          placeholder="consumer@example.com"
          value={form.consumer_email_id}
          onChange={(e) =>
            setForm({ ...form, consumer_email_id: e.target.value })
          }
        />
      </div>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={saving}>
          {saving ? <Spinner /> : <Plus className="h-4 w-4" aria-hidden />}
          {saving ? "Saving…" : editingId ? "Update" : "Create"}
        </Button>
        {editingId ? (
          <Button type="button" variant="secondary" onClick={resetForm}>
            Cancel
          </Button>
        ) : null}
      </div>
    </form>
  );

  return (
    <AppShell>
      <PageHeader
        title="Customers"
        description="Manage consumers for the selected client."
        action={
          <Button onClick={() => void load()} variant="secondary">
            <RefreshCw className="h-4 w-4" aria-hidden />
            Refresh
          </Button>
        }
      />

      {error ? <ErrorBanner message={error} /> : null}

      {!clientEmailId ? (
        <EmptyState message="Select a client in the header to view customers." />
      ) : (
        <SplitLayout
          sidebar={
            canEditCustomers ? (
              <Card className="hidden lg:block">
                <CardHeader>
                  <CardTitle>
                    {editingId ? "Edit consumer" : "Add consumer"}
                  </CardTitle>
                  <CardDescription>
                    Phone and email for outbound campaigns.
                  </CardDescription>
                </CardHeader>
                {consumerForm}
              </Card>
            ) : (
              <Card className="hidden lg:block">
                <CardHeader>
                  <CardTitle>Read-only access</CardTitle>
                  <CardDescription>
                    Your role can view customers but cannot create or edit records.
                  </CardDescription>
                </CardHeader>
              </Card>
            )
          }
        >
          <Card padding={false}>
            <div className="border-b border-border px-5 py-4 sm:px-6">
              <CardTitle>All consumers</CardTitle>
              <CardDescription className="mt-1">
                {customers.length} record{customers.length === 1 ? "" : "s"}
              </CardDescription>
            </div>
            <div className="p-2 sm:p-4">
              {loading ? (
                <div className="flex items-center gap-2 px-3 py-8 text-sm text-muted-foreground">
                  <Spinner />
                  Loading customers…
                </div>
              ) : customers.length === 0 ? (
                <EmptyState message="No customers for this client yet." />
              ) : (
                <Table>
                  <TableHead>
                    <TableHeaderCell>Phone</TableHeaderCell>
                    <TableHeaderCell>Email</TableHeaderCell>
                    {canEditCustomers ? (
                      <TableHeaderCell className="text-right">Actions</TableHeaderCell>
                    ) : null}
                  </TableHead>
                  <TableBody>
                    {customers.map((customer) => (
                      <TableRow
                        key={customer.id}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => setHistoryCustomer(customer)}
                      >
                        <TableCell className="font-medium">
                          {customer.consumer_phone_number}
                        </TableCell>
                        <TableCell>{customer.consumer_email_id}</TableCell>
                        {canEditCustomers ? (
                          <TableCell className="text-right">
                            <div
                              className="flex justify-end gap-1"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <Button
                                variant="ghost"
                                size="icon"
                                aria-label="Edit customer"
                                onClick={() => startEdit(customer)}
                              >
                                <Pencil className="h-4 w-4" aria-hidden />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                aria-label="Delete customer"
                                onClick={() => void handleDelete(customer.id)}
                              >
                                <Trash2 className="h-4 w-4 text-red-600" aria-hidden />
                              </Button>
                            </div>
                          </TableCell>
                        ) : null}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </div>
          </Card>
        </SplitLayout>
      )}

      {canEditCustomers && clientEmailId ? (
        <>
          <Button
            type="button"
            size="icon"
            className="fixed bottom-20 right-4 z-30 h-12 w-12 rounded-full shadow-[var(--shadow-elevated)] lg:hidden"
            aria-label="Add consumer"
            onClick={() => {
              setEditingId(null);
              setForm(emptyConsumerForm);
              setMobileFormOpen(true);
            }}
          >
            <Plus className="h-5 w-5" aria-hidden />
          </Button>

          <Sheet open={mobileFormOpen} onOpenChange={setMobileFormOpen}>
            <SheetContent side="bottom">
              <SheetHeader>
                <SheetTitle>
                  {editingId ? "Edit consumer" : "Add consumer"}
                </SheetTitle>
                <SheetDescription>
                  Phone and email for outbound campaigns.
                </SheetDescription>
              </SheetHeader>
              {consumerForm}
            </SheetContent>
          </Sheet>
        </>
      ) : null}

      <CustomerCallHistorySheet
        open={historyCustomer !== null}
        onOpenChange={(open) => !open && setHistoryCustomer(null)}
        clientEmailId={clientEmailId}
        customerId={historyCustomer?.id ?? null}
        customerPhone={historyCustomer?.consumer_phone_number}
        customerEmail={historyCustomer?.consumer_email_id}
      />
    </AppShell>
  );
}
