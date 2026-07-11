"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { AdminRouteGuard } from "@/components/admin-route-guard";
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
  Spinner,
  SplitLayout,
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
import type { CallJob, CallJobListResponse } from "@/lib/types";
import { formatDate, statusColor } from "@/lib/utils";
import { PhoneCall, RefreshCw } from "lucide-react";

export default function CallJobsPage() {
  const { canManageData } = usePermissions();
  const { clientEmailId, clientBusinessPhoneNumber, ready } = useClientScope();
  const [jobs, setJobs] = useState<CallJob[]>([]);
  const [selected, setSelected] = useState<CallJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadJobs() {
    if (!ready || !clientEmailId) return;
    setLoading(true);
    setError(null);
    try {
      const scope = clientScopeQuery(clientEmailId);
      const phoneQuery = clientBusinessPhoneNumber
        ? `&client_business_phone_number=${encodeURIComponent(clientBusinessPhoneNumber)}`
        : "";
      const data = await apiFetch<CallJobListResponse>(
        `v1/call-jobs?${scope}${phoneQuery}&limit=20`,
      );
      setJobs(data.jobs);
    } catch (e) {
      setError(errorMessageFromUnknown(e, "Failed to load jobs"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!ready) return;
    void loadJobs();
    const timer = setInterval(() => void loadJobs(), 5000);
    return () => clearInterval(timer);
  }, [clientEmailId, clientBusinessPhoneNumber, ready]);

  async function triggerJob() {
    if (!clientBusinessPhoneNumber) {
      setError("Selected client has no business phone configured.");
      return;
    }
    if (!clientEmailId) return;
    setTriggering(true);
    setError(null);
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
      setSelected(job);
      await loadJobs();
    } catch (e) {
      setError(errorMessageFromUnknown(e, "Failed to trigger job"));
    } finally {
      setTriggering(false);
    }
  }

  async function viewJob(jobId: string) {
    if (!clientEmailId) return;
    try {
      const scope = clientScopeQuery(clientEmailId);
      const job = await apiFetch<CallJob>(`v1/call-jobs/${jobId}?${scope}`);
      setSelected(job);
    } catch (e) {
      setError(errorMessageFromUnknown(e, "Failed to load job"));
    }
  }

  return (
    <AdminRouteGuard>
      <AppShell>
        <PageHeader
          title="Call Jobs"
          description="Trigger outbound voice campaigns and monitor progress."
        />

        {error ? <ErrorBanner message={error} /> : null}

        {!clientEmailId ? (
          <EmptyState message="Select a client in the header to view call jobs." />
        ) : (
          <SplitLayout
            className="lg:grid-cols-[minmax(260px,300px)_1fr]"
            sidebar={
              <Card>
                <CardHeader>
                  <CardTitle>
                    {canManageData ? "Trigger campaign" : "Monitor jobs"}
                  </CardTitle>
                  <CardDescription>
                    {canManageData
                      ? "Uses the business phone from the active client."
                      : "View outbound call progress for your account."}
                  </CardDescription>
                </CardHeader>
                {canManageData ? (
                  <Button
                    className="w-full"
                    onClick={() => void triggerJob()}
                    disabled={triggering || !clientBusinessPhoneNumber}
                  >
                    {triggering ? (
                      <Spinner />
                    ) : (
                      <PhoneCall className="h-4 w-4" aria-hidden />
                    )}
                    {triggering ? "Triggering…" : "Start outbound calls"}
                  </Button>
                ) : null}
                <Button
                  variant="secondary"
                  className="mt-2 w-full"
                  onClick={() => void loadJobs()}
                >
                  <RefreshCw className="h-4 w-4" aria-hidden />
                  Refresh list
                </Button>
              </Card>
            }
          >
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Recent jobs</CardTitle>
                </CardHeader>
                {loading && jobs.length === 0 ? (
                  <div className="flex items-center gap-2 text-sm text-zinc-500">
                    <Spinner />
                    Loading jobs…
                  </div>
                ) : jobs.length === 0 ? (
                  <EmptyState message="No call jobs yet." />
                ) : (
                  <div className="space-y-2">
                    {jobs.map((job) => (
                      <button
                        key={job.id}
                        type="button"
                        onClick={() => void viewJob(job.id)}
                        className="flex w-full items-center justify-between rounded-lg border border-zinc-100 bg-zinc-50/50 px-4 py-3 text-left transition-colors hover:border-zinc-200 hover:bg-white"
                      >
                        <div>
                          <p className="font-medium text-zinc-900">
                            {job.client_business_phone_number}
                          </p>
                          <p className="mt-0.5 text-xs text-zinc-500">
                            {formatDate(job.created_at)}
                          </p>
                        </div>
                        <div className="text-right">
                          <Badge className={statusColor(job.status)}>
                            {job.status}
                          </Badge>
                          <p className="mt-1 text-xs text-zinc-500">
                            {job.calls_completed}/{job.total_customers} calls
                          </p>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </Card>

              {selected ? (
                <Card>
                  <div className="mb-4 flex items-center justify-between gap-3">
                    <CardTitle>Job details</CardTitle>
                    <Badge className={statusColor(selected.status)}>
                      {selected.status}
                    </Badge>
                  </div>
                  <dl className="grid gap-4 text-sm sm:grid-cols-2">
                    <div>
                      <dt className="text-xs font-medium uppercase tracking-wide text-zinc-400">
                        Job ID
                      </dt>
                      <dd className="mt-1 break-all font-mono text-xs text-zinc-700">
                        {selected.id}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs font-medium uppercase tracking-wide text-zinc-400">
                        Progress
                      </dt>
                      <dd className="mt-1 font-medium text-zinc-900">
                        {selected.calls_completed} / {selected.total_customers}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs font-medium uppercase tracking-wide text-zinc-400">
                        Started
                      </dt>
                      <dd className="mt-1 text-zinc-700">
                        {formatDate(selected.started_at)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs font-medium uppercase tracking-wide text-zinc-400">
                        Completed
                      </dt>
                      <dd className="mt-1 text-zinc-700">
                        {formatDate(selected.completed_at)}
                      </dd>
                    </div>
                  </dl>
                  {selected.error_message ? (
                    <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                      {selected.error_message}
                    </p>
                  ) : null}
                  {selected.results?.length ? (
                    <div className="mt-4">
                      <Table>
                        <TableHead>
                          <TableHeaderCell>Consumer</TableHeaderCell>
                          <TableHeaderCell>Result</TableHeaderCell>
                          <TableHeaderCell>Detail</TableHeaderCell>
                        </TableHead>
                        <TableBody>
                          {selected.results.map((result) => (
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
                              <TableCell className="text-zinc-600">
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
          </SplitLayout>
        )}
      </AppShell>
    </AdminRouteGuard>
  );
}
