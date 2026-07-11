"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import {
  Badge,
  Button,
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorBanner,
  PageHeader,
  Select,
  Spinner,
  SuccessBanner,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "@/components/ui";
import { apiFetch, errorMessageFromUnknown } from "@/lib/api-client";
import { clientScopeQuery, useClientScope } from "@/contexts/client-scope-context";
import { usePermissions } from "@/hooks/use-permissions";
import type {
  CallJob,
  CallJobListResponse,
  CallScheduleValue,
  Customer,
  CustomerListResponse,
  CustomerStatusValue,
} from "@/lib/types";
import { formatDate, statusColor } from "@/lib/utils";
import { Megaphone, RefreshCw } from "lucide-react";

export default function CampaignsPage() {
  const { canManageOwnCustomers } = usePermissions();
  const { clientEmailId, clientBusinessPhoneNumber, ready } = useClientScope();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [jobs, setJobs] = useState<CallJob[]>([]);
  const [selectedJob, setSelectedJob] = useState<CallJob | null>(null);
  const [loadingCustomers, setLoadingCustomers] = useState(true);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const scheduledCount = customers.filter(
    (c) => c.call_schedule === "yes" && c.status === "READY",
  ).length;

  async function loadCustomers() {
    if (!ready || !clientEmailId) {
      setCustomers([]);
      setLoadingCustomers(false);
      return;
    }
    setLoadingCustomers(true);
    setError(null);
    try {
      const scope = clientScopeQuery(clientEmailId);
      const data = await apiFetch<CustomerListResponse>(`v1/customers?${scope}`);
      setCustomers(data.customers);
    } catch (e) {
      setError(errorMessageFromUnknown(e, "Failed to load customers"));
    } finally {
      setLoadingCustomers(false);
    }
  }

  async function loadJobs() {
    if (!ready || !clientEmailId) {
      setJobs([]);
      setLoadingJobs(false);
      return;
    }
    setLoadingJobs(true);
    try {
      const scope = clientScopeQuery(clientEmailId);
      const phoneQuery = clientBusinessPhoneNumber
        ? `&client_business_phone_number=${encodeURIComponent(clientBusinessPhoneNumber)}`
        : "";
      const data = await apiFetch<CallJobListResponse>(
        `v1/call-jobs?${scope}${phoneQuery}&limit=10`,
      );
      setJobs(data.jobs);
    } catch (e) {
      setError(errorMessageFromUnknown(e, "Failed to load campaigns"));
    } finally {
      setLoadingJobs(false);
    }
  }

  useEffect(() => {
    void loadCustomers();
    void loadJobs();
    const timer = setInterval(() => void loadJobs(), 5000);
    return () => clearInterval(timer);
  }, [clientEmailId, clientBusinessPhoneNumber, ready]);

  async function updateCustomerField(
    customer: Customer,
    patch: { call_schedule?: CallScheduleValue; status?: CustomerStatusValue },
  ) {
    if (!clientEmailId) return;
    setUpdatingId(customer.id);
    setError(null);
    setSuccess(null);
    try {
      const scope = clientScopeQuery(clientEmailId);
      const updated = await apiFetch<Customer>(
        `v1/customers/${customer.id}?${scope}`,
        {
          method: "PUT",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(patch),
        },
      );
      setCustomers((current) =>
        current.map((row) => (row.id === updated.id ? updated : row)),
      );
    } catch (e) {
      setError(errorMessageFromUnknown(e, "Failed to update customer"));
    } finally {
      setUpdatingId(null);
    }
  }

  async function triggerCampaign() {
    if (!clientBusinessPhoneNumber) {
      setError("Selected client has no business phone configured.");
      return;
    }
    if (!clientEmailId) return;
    if (scheduledCount === 0) {
      setError(
        "Set call schedule to Yes and status to Ready for at least one customer.",
      );
      return;
    }
    setTriggering(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await apiFetch<{ job_id: string }>("v1/call-jobs/trigger", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          client_business_phone_number: clientBusinessPhoneNumber,
          client_email_id: clientEmailId,
        }),
      });
      const scope = clientScopeQuery(clientEmailId);
      const job = await apiFetch<CallJob>(`v1/call-jobs/${result.job_id}?${scope}`);
      setSelectedJob(job);
      setSuccess(
        `Campaign started — ${scheduledCount} customer${scheduledCount === 1 ? "" : "s"} queued.`,
      );
      await loadJobs();
    } catch (e) {
      setError(errorMessageFromUnknown(e, "Failed to trigger campaign"));
    } finally {
      setTriggering(false);
    }
  }

  async function viewJob(jobId: string) {
    if (!clientEmailId) return;
    try {
      const scope = clientScopeQuery(clientEmailId);
      const job = await apiFetch<CallJob>(`v1/call-jobs/${jobId}?${scope}`);
      setSelectedJob(job);
    } catch (e) {
      setError(errorMessageFromUnknown(e, "Failed to load campaign job"));
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Campaign"
        description="Choose customers to call, then trigger an outbound voice campaign from the business phone."
        action={
          <Button variant="secondary" onClick={() => { void loadCustomers(); void loadJobs(); }}>
            <RefreshCw className="h-4 w-4" aria-hidden />
            Refresh
          </Button>
        }
      />

      {error ? <ErrorBanner message={error} /> : null}
      {success ? <SuccessBanner message={success} /> : null}

      {!clientEmailId ? (
        <EmptyState message="Select a client in the header to manage campaigns." />
      ) : (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Trigger campaign</CardTitle>
              <CardDescription>
                Calls customers with call schedule <strong>Yes</strong> and status{" "}
                <strong>Ready</strong> using business phone{" "}
                {clientBusinessPhoneNumber ?? "—"}.
              </CardDescription>
            </CardHeader>
            {canManageOwnCustomers ? (
              <Button
                onClick={() => void triggerCampaign()}
                disabled={triggering || !clientBusinessPhoneNumber || scheduledCount === 0}
              >
                {triggering ? <Spinner /> : <Megaphone className="h-4 w-4" aria-hidden />}
                {triggering ? "Starting…" : `Trigger campaign (${scheduledCount} queued)`}
              </Button>
            ) : (
              <p className="text-sm text-muted-foreground">
                You can view campaign progress but cannot trigger calls with your role.
              </p>
            )}
          </Card>

          <Card padding={false}>
            <div className="border-b border-border px-5 py-4 sm:px-6">
              <CardTitle>Customers</CardTitle>
              <CardDescription className="mt-1">
                Set call schedule to Yes to include a customer in the next campaign.
                Status starts as Ready for new customers; after a call it becomes
                Meeting scheduled or No meeting automatically.
              </CardDescription>
            </div>
            <div className="p-2 sm:p-4">
              {loadingCustomers ? (
                <div className="flex items-center gap-2 px-3 py-8 text-sm text-muted-foreground">
                  <Spinner />
                  Loading customers…
                </div>
              ) : customers.length === 0 ? (
                <EmptyState message="No customers yet. Add consumers on the Customers page." />
              ) : (
                <Table>
                  <TableHead>
                    <TableHeaderCell>Phone</TableHeaderCell>
                    <TableHeaderCell>Email</TableHeaderCell>
                    <TableHeaderCell>Call schedule</TableHeaderCell>
                    <TableHeaderCell>Status</TableHeaderCell>
                  </TableHead>
                  <TableBody>
                    {customers.map((customer) => (
                      <TableRow key={customer.id}>
                        <TableCell className="font-medium">
                          {customer.consumer_phone_number}
                        </TableCell>
                        <TableCell>{customer.consumer_email_id}</TableCell>
                        <TableCell>
                          <Select
                            aria-label={`Call schedule for ${customer.consumer_phone_number}`}
                            value={customer.call_schedule}
                            disabled={!canManageOwnCustomers || updatingId === customer.id}
                            onChange={(e) =>
                              void updateCustomerField(customer, {
                                call_schedule: e.target.value as CallScheduleValue,
                              })
                            }
                          >
                            <option value="no">No</option>
                            <option value="yes">Yes</option>
                          </Select>
                        </TableCell>
                        <TableCell>
                          <Select
                            aria-label={`Status for ${customer.consumer_phone_number}`}
                            value={customer.status}
                            disabled={!canManageOwnCustomers || updatingId === customer.id}
                            onChange={(e) =>
                              void updateCustomerField(customer, {
                                status: e.target.value as CustomerStatusValue,
                              })
                            }
                          >
                            <option value="READY">Ready</option>
                            <option value="MEETING_SCHEDULED">Meeting scheduled</option>
                            <option value="MEETING_NOT_SCHEDULED">No meeting</option>
                          </Select>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </div>
          </Card>

          <Card padding={false}>
            <div className="border-b border-border px-5 py-4 sm:px-6">
              <CardTitle>Recent campaigns</CardTitle>
            </div>
            <div className="p-2 sm:p-4">
              {loadingJobs && jobs.length === 0 ? (
                <div className="flex items-center gap-2 px-3 py-8 text-sm text-muted-foreground">
                  <Spinner />
                  Loading campaigns…
                </div>
              ) : jobs.length === 0 ? (
                <EmptyState message="No campaigns run yet." />
              ) : (
                <div className="space-y-2">
                  {jobs.map((job) => (
                    <button
                      key={job.id}
                      type="button"
                      onClick={() => void viewJob(job.id)}
                      className="flex w-full items-center justify-between rounded-lg border border-border bg-muted/30 px-4 py-3 text-left transition-colors hover:bg-card"
                    >
                      <div>
                        <p className="font-medium">{formatDate(job.created_at)}</p>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {job.client_business_phone_number}
                        </p>
                      </div>
                      <div className="text-right">
                        <Badge className={statusColor(job.status)}>{job.status}</Badge>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {job.calls_completed}/{job.total_customers} calls
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </Card>

          {selectedJob ? (
            <Card>
              <div className="mb-4 flex items-center justify-between gap-3">
                <CardTitle>Campaign details</CardTitle>
                <Badge className={statusColor(selectedJob.status)}>
                  {selectedJob.status}
                </Badge>
              </div>
              <dl className="grid gap-4 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Progress
                  </dt>
                  <dd className="mt-1 font-medium">
                    {selectedJob.calls_completed} / {selectedJob.total_customers}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Started
                  </dt>
                  <dd className="mt-1">{formatDate(selectedJob.started_at)}</dd>
                </div>
              </dl>
              {selectedJob.results?.length ? (
                <div className="mt-4">
                  <Table>
                    <TableHead>
                      <TableHeaderCell>Consumer</TableHeaderCell>
                      <TableHeaderCell>Result</TableHeaderCell>
                      <TableHeaderCell>Detail</TableHeaderCell>
                    </TableHead>
                    <TableBody>
                      {selectedJob.results.map((result) => (
                        <TableRow
                          key={`${result.customer_id}-${result.consumer_phone_number}`}
                        >
                          <TableCell>{result.consumer_phone_number}</TableCell>
                          <TableCell>
                            <Badge
                              className={
                                result.success
                                  ? "bg-emerald-50 text-emerald-700"
                                  : "bg-red-50 text-red-700"
                              }
                            >
                              {result.success ? "success" : "failed"}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {result.detail}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ) : null}
            </Card>
          ) : null}
        </div>
      )}
    </AppShell>
  );
}
