"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  PageHeader,
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
    <AppShell>
      <PageHeader
        title="Call Jobs"
        description="Trigger outbound voice campaigns and monitor progress."
      />

      {error ? <ErrorBanner message={error} /> : null}

      {!clientEmailId ? (
        <EmptyState message="Select a client in the header to view call jobs." />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
          {canManageData ? (
            <Card>
              <h2 className="font-semibold text-slate-900">Trigger campaign</h2>
              <p className="mt-2 text-sm text-slate-600">
                Uses the business phone from the active client in the header.
              </p>
              <Button
                className="mt-4 w-full"
                onClick={() => void triggerJob()}
                disabled={triggering || !clientBusinessPhoneNumber}
              >
                <PhoneCall className="h-4 w-4" />
                {triggering ? "Triggering…" : "Start outbound calls"}
              </Button>
              <Button
                variant="secondary"
                className="mt-2 w-full"
                onClick={() => void loadJobs()}
              >
                <RefreshCw className="h-4 w-4" />
                Refresh list
              </Button>
            </Card>
          ) : (
            <Card>
              <h2 className="font-semibold text-slate-900">Monitor jobs</h2>
              <p className="mt-2 text-sm text-slate-600">
                View outbound call progress for your account.
              </p>
              <Button
                variant="secondary"
                className="mt-4 w-full"
                onClick={() => void loadJobs()}
              >
                <RefreshCw className="h-4 w-4" />
                Refresh list
              </Button>
            </Card>
          )}

          <div className="space-y-4">
            <Card>
              <h2 className="font-semibold text-slate-900">Recent jobs</h2>
              {loading && jobs.length === 0 ? (
                <p className="mt-4 text-sm text-slate-500">Loading…</p>
              ) : jobs.length === 0 ? (
                <EmptyState message="No call jobs yet." />
              ) : (
                <div className="mt-4 space-y-2">
                  {jobs.map((job) => (
                    <button
                      key={job.id}
                      type="button"
                      onClick={() => void viewJob(job.id)}
                      className="flex w-full items-center justify-between rounded-xl border border-slate-100 bg-slate-50 px-4 py-3 text-left hover:bg-white"
                    >
                      <div>
                        <p className="font-medium">{job.client_business_phone_number}</p>
                        <p className="text-xs text-slate-500">
                          {formatDate(job.created_at)}
                        </p>
                      </div>
                      <div className="text-right">
                        <Badge className={statusColor(job.status)}>
                          {job.status}
                        </Badge>
                        <p className="mt-1 text-xs text-slate-500">
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
                <div className="flex items-center justify-between">
                  <h2 className="font-semibold text-slate-900">Job details</h2>
                  <Badge className={statusColor(selected.status)}>
                    {selected.status}
                  </Badge>
                </div>
                <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="text-slate-500">Job ID</dt>
                    <dd className="break-all font-mono text-xs">{selected.id}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Progress</dt>
                    <dd>
                      {selected.calls_completed} / {selected.total_customers}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Started</dt>
                    <dd>{formatDate(selected.started_at)}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Completed</dt>
                    <dd>{formatDate(selected.completed_at)}</dd>
                  </div>
                </dl>
                {selected.error_message ? (
                  <p className="mt-3 text-sm text-red-600">
                    {selected.error_message}
                  </p>
                ) : null}
                {selected.results?.length ? (
                  <div className="mt-4 overflow-x-auto">
                    <table className="min-w-full text-left text-sm">
                      <thead className="text-slate-500">
                        <tr>
                          <th className="px-2 py-2">Consumer</th>
                          <th className="px-2 py-2">Result</th>
                          <th className="px-2 py-2">Detail</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selected.results.map((result) => (
                          <tr
                            key={`${result.customer_id}-${result.consumer_phone_number}`}
                            className="border-t border-slate-100"
                          >
                            <td className="px-2 py-2">
                              {result.consumer_phone_number}
                            </td>
                            <td className="px-2 py-2">
                              <Badge
                                className={
                                  result.success
                                    ? "bg-emerald-100 text-emerald-800"
                                    : "bg-red-100 text-red-800"
                                }
                              >
                                {result.success ? "success" : "failed"}
                              </Badge>
                            </td>
                            <td className="px-2 py-2 text-slate-600">
                              {result.detail}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}
              </Card>
            ) : null}
          </div>
        </div>
      )}
    </AppShell>
  );
}
