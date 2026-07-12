"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { ConsumerCallHistorySheet } from "@/components/consumer-call-history-sheet";
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
  Textarea,
} from "@/components/ui";
import { PhoneInput } from "@/components/phone-input";
import { apiFetch } from "@/lib/api-client";
import { clientScopeQuery, useClientScope } from "@/contexts/client-scope-context";
import { usePermissions } from "@/hooks/use-permissions";
import {
  combinePhoneParts,
  EMPTY_PHONE_FIELDS,
  formatPhoneDisplay,
  splitStoredPhone,
} from "@/lib/phone";
import type { Consumer, ConsumerListResponse } from "@/lib/types";
import { Pencil, Plus, RefreshCw, Trash2 } from "lucide-react";

const emptyConsumerForm = {
  consumer_name: "",
  consumer_address: "",
  consumer_phone: { ...EMPTY_PHONE_FIELDS },
  consumer_email_id: "",
};

export default function ConsumersPage() {
  const searchParams = useSearchParams();
  const { canManageData, canManageOwnConsumers } = usePermissions();
  const { selectedClient, clientEmailId, ready } = useClientScope();
  const [consumers, setConsumers] = useState<Consumer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [form, setForm] = useState(emptyConsumerForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [mobileFormOpen, setMobileFormOpen] = useState(false);
  const [historyConsumer, setHistoryConsumer] = useState<Consumer | null>(null);

  const canEditConsumers = canManageData || canManageOwnConsumers;

  async function load() {
    if (!ready || !clientEmailId) {
      setConsumers([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const query = `v1/consumers?client_email_id=${encodeURIComponent(clientEmailId)}`;
      const data = await apiFetch<ConsumerListResponse>(query);
      setConsumers(data.consumers);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load consumers");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [clientEmailId, ready]);

  useEffect(() => {
    const consumerParam = searchParams.get("consumer");
    if (!consumerParam || consumers.length === 0) {
      return;
    }
    const consumerId = Number(consumerParam);
    if (!Number.isFinite(consumerId)) {
      return;
    }
    const match = consumers.find((consumer) => consumer.id === consumerId);
    if (match) {
      setHistoryConsumer(match);
    }
  }, [consumers, searchParams]);

  function buildCreatePayload() {
    if (!selectedClient?.client_business_phone_number) {
      throw new Error("Selected client has no business phone configured.");
    }
    return {
      client_business_phone_number: selectedClient.client_business_phone_number,
      client_name: selectedClient.client_name || "Client",
      client_email_id: selectedClient.client_email_id,
      consumer_phone_number: combinePhoneParts(form.consumer_phone),
      consumer_email_id: form.consumer_email_id.trim().toLowerCase(),
      consumer_name: form.consumer_name.trim(),
      consumer_address: form.consumer_address.trim(),
    };
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!clientEmailId || saving) return;
    setError(null);
    setPhoneError(null);
    setSaving(true);
    try {
      const scope = clientScopeQuery(clientEmailId);
      let consumerPhone: string;
      try {
        consumerPhone = combinePhoneParts(form.consumer_phone);
      } catch (e) {
        const message = e instanceof Error ? e.message : "Invalid phone number";
        setPhoneError(message);
        setSaving(false);
        return;
      }
      const consumerEmail = form.consumer_email_id.trim().toLowerCase();
      if (!consumerPhone) {
        setPhoneError("Consumer phone number is required.");
        setSaving(false);
        return;
      }
      if (!consumerEmail) {
        throw new Error("Consumer email is required.");
      }
      if (editingId) {
        await apiFetch(`v1/consumers/${editingId}?${scope}`, {
          method: "PUT",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            consumer_phone_number: consumerPhone,
            consumer_email_id: consumerEmail,
            consumer_name: form.consumer_name.trim(),
            consumer_address: form.consumer_address.trim(),
          }),
        });
      } else {
        await apiFetch("v1/consumers", {
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
    if (!clientEmailId || !confirm("Delete this consumer?")) return;
    try {
      const scope = clientScopeQuery(clientEmailId);
      await apiFetch(`v1/consumers/${id}?${scope}`, { method: "DELETE" });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  function startEdit(consumer: Consumer) {
    setEditingId(consumer.id);
    setForm({
      consumer_name: consumer.consumer_name,
      consumer_address: consumer.consumer_address,
      consumer_phone: splitStoredPhone(consumer.consumer_phone_number),
      consumer_email_id: consumer.consumer_email_id,
    });
    setPhoneError(null);
    setMobileFormOpen(true);
  }

  function resetForm() {
    setEditingId(null);
    setForm(emptyConsumerForm);
    setPhoneError(null);
    setMobileFormOpen(false);
  }

  const consumerForm = (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <div>
        <Label htmlFor="consumer_name">Consumer name</Label>
        <Input
          id="consumer_name"
          autoComplete="name"
          maxLength={255}
          placeholder="Consumer name"
          value={form.consumer_name}
          onChange={(e) =>
            setForm({ ...form, consumer_name: e.target.value })
          }
        />
      </div>
      <PhoneInput
        label="Consumer phone"
        countryCodeId="consumer_country_code"
        nationalNumberId="consumer_phone"
        value={form.consumer_phone}
        required
        error={phoneError}
        hint="Stored as digits only (e.g. 919876543210)."
        onChange={(consumer_phone) => {
          setPhoneError(null);
          setForm({ ...form, consumer_phone });
        }}
      />
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
      <div>
        <Label htmlFor="consumer_address">Consumer address</Label>
        <Textarea
          id="consumer_address"
          autoComplete="street-address"
          maxLength={2000}
          placeholder="Consumer address"
          rows={3}
          value={form.consumer_address}
          onChange={(e) =>
            setForm({ ...form, consumer_address: e.target.value })
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
        title="Consumers"
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
        <EmptyState message="Select a client in the header to view consumers." />
      ) : (
        <SplitLayout
          sidebar={
            canEditConsumers ? (
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
                    Your role can view consumers but cannot create or edit records.
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
                {consumers.length} record{consumers.length === 1 ? "" : "s"}
              </CardDescription>
            </div>
            <div className="p-2 sm:p-4">
              {loading ? (
                <div className="flex items-center gap-2 px-3 py-8 text-sm text-muted-foreground">
                  <Spinner />
                  Loading consumers…
                </div>
              ) : consumers.length === 0 ? (
                <EmptyState message="No consumers for this client yet." />
              ) : (
                <Table>
                  <TableHead>
                    <TableHeaderCell>Name</TableHeaderCell>
                    <TableHeaderCell>Phone</TableHeaderCell>
                    <TableHeaderCell>Email</TableHeaderCell>
                    <TableHeaderCell>Address</TableHeaderCell>
                    {canEditConsumers ? (
                      <TableHeaderCell className="text-right">Actions</TableHeaderCell>
                    ) : null}
                  </TableHead>
                  <TableBody>
                    {consumers.map((consumer) => (
                      <TableRow
                        key={consumer.id}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => setHistoryConsumer(consumer)}
                      >
                        <TableCell className="font-medium">
                          {consumer.consumer_name || "—"}
                        </TableCell>
                        <TableCell className="font-medium">
                          {formatPhoneDisplay(consumer.consumer_phone_number)}
                        </TableCell>
                        <TableCell>{consumer.consumer_email_id}</TableCell>
                        <TableCell className="max-w-xs whitespace-normal">
                          {consumer.consumer_address || "—"}
                        </TableCell>
                        {canEditConsumers ? (
                          <TableCell className="text-right">
                            <div
                              className="flex justify-end gap-1"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <Button
                                variant="ghost"
                                size="icon"
                                aria-label="Edit consumer"
                                onClick={() => startEdit(consumer)}
                              >
                                <Pencil className="h-4 w-4" aria-hidden />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                aria-label="Delete consumer"
                                onClick={() => void handleDelete(consumer.id)}
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

      {canEditConsumers && clientEmailId ? (
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

      <ConsumerCallHistorySheet
        open={historyConsumer !== null}
        onOpenChange={(open) => !open && setHistoryConsumer(null)}
        clientEmailId={clientEmailId}
        consumerId={historyConsumer?.id ?? null}
        consumerPhone={historyConsumer?.consumer_phone_number}
        consumerEmail={historyConsumer?.consumer_email_id}
      />
    </AppShell>
  );
}
