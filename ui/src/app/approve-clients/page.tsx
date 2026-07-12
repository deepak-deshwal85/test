"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { AdminRouteGuard } from "@/components/admin-route-guard";
import { DeleteClientAccountSection } from "@/components/delete-client-account-section";
import {
  Badge,
  Button,
  Card,
  CardDescription,
  CardTitle,
  EmptyState,
  ErrorBanner,
  PageHeader,
  PageSection,
  Spinner,
  SuccessBanner,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "@/components/ui";
import { PhoneInput } from "@/components/phone-input";
import { apiFetch } from "@/lib/api-client";
import { useClientScope } from "@/contexts/client-scope-context";
import {
  combinePhoneParts,
  EMPTY_PHONE_FIELDS,
  formatPhoneDisplay,
  type PhoneFields,
} from "@/lib/phone";
import type { ClientAdminListResponse, ClientAdminProfile } from "@/lib/types";
import { CheckCircle2, RefreshCw } from "lucide-react";

export default function ApproveClientsPage() {
  const { refresh: refreshScope } = useClientScope();
  const [clients, setClients] = useState<ClientAdminProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [businessPhones, setBusinessPhones] = useState<
    Record<string, PhoneFields>
  >({});
  const [phoneErrors, setPhoneErrors] = useState<Record<string, string>>({});
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
    const phoneFields =
      businessPhones[client.client_email_id] ?? { ...EMPTY_PHONE_FIELDS };
    let businessPhone: string;
    try {
      businessPhone = combinePhoneParts(phoneFields);
    } catch (e) {
      const message = e instanceof Error ? e.message : "Invalid business phone";
      setPhoneErrors((current) => ({
        ...current,
        [client.client_email_id]: message,
      }));
      setError(message);
      return;
    }

    setApprovingEmail(client.client_email_id);
    setError(null);
    setSuccessMessage(null);
    setPhoneErrors((current) => {
      const next = { ...current };
      delete next[client.client_email_id];
      return next;
    });
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
              <RefreshCw className="h-4 w-4" aria-hidden />
              Refresh
            </Button>
          }
        />

        {error ? <ErrorBanner message={error} /> : null}
        {successMessage ? <SuccessBanner message={successMessage} /> : null}

        {loading ? (
          <div className="flex items-center gap-2 text-sm text-zinc-500">
            <Spinner />
            Loading clients…
          </div>
        ) : clients.length === 0 ? (
          <EmptyState message="Clients appear here after they sign in via SSO for the first time." />
        ) : (
          <PageSection className="space-y-6">
            <Card padding={false}>
              <div className="border-b border-zinc-100 px-5 py-4 sm:px-6">
                <CardTitle>Pending approval ({pending.length})</CardTitle>
                <CardDescription className="mt-1">
                  Enter a business phone number and approve to grant console access.
                </CardDescription>
              </div>
              <div className="p-2 sm:p-4">
                {pending.length === 0 ? (
                  <p className="px-3 py-6 text-sm text-zinc-500">No pending clients.</p>
                ) : (
                  <Table>
                    <TableHead>
                      <TableHeaderCell>Email</TableHeaderCell>
                      <TableHeaderCell>Name</TableHeaderCell>
                      <TableHeaderCell>Personal phone</TableHeaderCell>
                      <TableHeaderCell>Business phone</TableHeaderCell>
                      <TableHeaderCell>Action</TableHeaderCell>
                    </TableHead>
                    <TableBody>
                      {pending.map((client) => (
                        <TableRow key={client.id} className="align-top">
                          <TableCell>{client.client_email_id}</TableCell>
                          <TableCell>{client.client_name || "—"}</TableCell>
                          <TableCell>
                            {formatPhoneDisplay(client.client_phone_number)}
                          </TableCell>
                          <TableCell className="min-w-[220px]">
                            <PhoneInput
                              label="Business phone"
                              countryCodeId={`business_country_${client.id}`}
                              nationalNumberId={`business_phone_${client.id}`}
                              value={
                                businessPhones[client.client_email_id] ?? {
                                  ...EMPTY_PHONE_FIELDS,
                                }
                              }
                              required
                              hideLabel
                              error={phoneErrors[client.client_email_id]}
                              onChange={(value) => {
                                setPhoneErrors((current) => {
                                  const next = { ...current };
                                  delete next[client.client_email_id];
                                  return next;
                                });
                                setBusinessPhones((current) => ({
                                  ...current,
                                  [client.client_email_id]: value,
                                }));
                              }}
                            />
                          </TableCell>
                          <TableCell>
                            <Button
                              size="sm"
                              onClick={() => void approveClient(client)}
                              disabled={approvingEmail === client.client_email_id}
                            >
                              {approvingEmail === client.client_email_id ? (
                                <Spinner />
                              ) : (
                                <CheckCircle2 className="h-4 w-4" aria-hidden />
                              )}
                              {approvingEmail === client.client_email_id
                                ? "Approving…"
                                : "Approve"}
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </div>
            </Card>

            <Card padding={false}>
              <div className="border-b border-zinc-100 px-5 py-4 sm:px-6">
                <CardTitle>Approved ({approved.length})</CardTitle>
              </div>
              <div className="p-2 sm:p-4">
                {approved.length === 0 ? (
                  <p className="px-3 py-6 text-sm text-zinc-500">No approved clients yet.</p>
                ) : (
                  <Table>
                    <TableHead>
                      <TableHeaderCell>Email</TableHeaderCell>
                      <TableHeaderCell>Name</TableHeaderCell>
                      <TableHeaderCell>Personal phone</TableHeaderCell>
                      <TableHeaderCell>Business phone</TableHeaderCell>
                      <TableHeaderCell>Status</TableHeaderCell>
                    </TableHead>
                    <TableBody>
                      {approved.map((client) => (
                        <TableRow key={client.id}>
                          <TableCell>{client.client_email_id}</TableCell>
                          <TableCell>{client.client_name || "—"}</TableCell>
                          <TableCell>
                            {formatPhoneDisplay(client.client_phone_number)}
                          </TableCell>
                          <TableCell>
                            {formatPhoneDisplay(client.client_business_phone_number)}
                          </TableCell>
                          <TableCell>
                            <Badge className="bg-emerald-50 text-emerald-700">
                              Approved
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </div>
            </Card>

            <DeleteClientAccountSection
              clients={clients}
              className="max-w-none"
              onDeleted={async () => {
                await load();
                await refreshScope();
              }}
            />
          </PageSection>
        )}
      </AppShell>
    </AdminRouteGuard>
  );
}
