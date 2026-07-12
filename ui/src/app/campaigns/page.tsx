"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
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
  Input,
  Label,
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
  Consumer,
  ConsumerListResponse,
  ConsumerStatusValue,
  VoiceAgentScheduleOverview,
} from "@/lib/types";
import { formatDate, statusColor } from "@/lib/utils";
import { ArrowRight, Bot, CalendarClock, Megaphone, RefreshCw } from "lucide-react";

const DAY_OPTIONS = [
  { value: 1, label: "Mon" },
  { value: 2, label: "Tue" },
  { value: 3, label: "Wed" },
  { value: 4, label: "Thu" },
  { value: 5, label: "Fri" },
  { value: 6, label: "Sat" },
  { value: 7, label: "Sun" },
] as const;

const TIMEZONE_OPTIONS = [
  "Asia/Kolkata",
  "Asia/Dubai",
  "Asia/Singapore",
  "Europe/London",
  "America/New_York",
  "America/Los_Angeles",
  "UTC",
] as const;

function formatScheduleDays(days: number[]): string {
  if (days.length === 0) return "—";
  const labels = DAY_OPTIONS.filter((d) => days.includes(d.value)).map((d) => d.label);
  if (labels.length === 7) return "Every day";
  if (
    labels.length === 5 &&
    [1, 2, 3, 4, 5].every((d) => days.includes(d))
  ) {
    return "Mon–Fri";
  }
  return labels.join(", ");
}

export default function CampaignsPage() {
  const scheduleRef = useRef<HTMLDivElement>(null);
  const { canManageOwnConsumers } = usePermissions();
  const { clientEmailId, clientBusinessPhoneNumber, ready } = useClientScope();

  const [overview, setOverview] = useState<VoiceAgentScheduleOverview | null>(null);
  const [consumers, setConsumers] = useState<Consumer[]>([]);
  const [jobs, setJobs] = useState<CallJob[]>([]);
  const [selectedJob, setSelectedJob] = useState<CallJob | null>(null);

  const [loadingOverview, setLoadingOverview] = useState(true);
  const [loadingConsumers, setLoadingConsumers] = useState(true);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [savingSchedule, setSavingSchedule] = useState(false);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [scheduleEnabled, setScheduleEnabled] = useState(false);
  const [runTime, setRunTime] = useState("09:00");
  const [daysOfWeek, setDaysOfWeek] = useState<number[]>([1, 2, 3, 4, 5]);
  const [timezone, setTimezone] = useState("Asia/Kolkata");

  const scope = clientScopeQuery(clientEmailId);
  const scopeSuffix = scope ? `?${scope}` : "";

  const readyCount =
    overview?.ready_consumer_count ??
    consumers.filter((c) => c.status === "READY").length;
  const hasActiveJob = overview?.has_active_job ?? false;
  const voiceConfig = overview?.voice_agent_config;

  async function loadOverview() {
    if (!ready || !clientEmailId) {
      setOverview(null);
      setLoadingOverview(false);
      return;
    }
    setLoadingOverview(true);
    try {
      const data = await apiFetch<VoiceAgentScheduleOverview>(
        `v1/voice-agent-schedule${scopeSuffix}`,
      );
      setOverview(data);
      setScheduleEnabled(data.schedule.enabled);
      setRunTime(data.schedule.run_time);
      setDaysOfWeek(data.schedule.days_of_week);
      setTimezone(data.schedule.timezone);
    } catch (e) {
      setError(errorMessageFromUnknown(e, "Failed to load campaign overview"));
    } finally {
      setLoadingOverview(false);
    }
  }

  async function loadConsumers() {
    if (!ready || !clientEmailId) {
      setConsumers([]);
      setLoadingConsumers(false);
      return;
    }
    setLoadingConsumers(true);
    try {
      const data = await apiFetch<ConsumerListResponse>(`v1/consumers?${scope}`);
      setConsumers(data.consumers);
    } catch (e) {
      setError(errorMessageFromUnknown(e, "Failed to load consumers"));
    } finally {
      setLoadingConsumers(false);
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
      const data = await apiFetch<CallJobListResponse>(
        `v1/call-jobs?${scope}&limit=10`,
      );
      setJobs(data.jobs);
    } catch (e) {
      setError(errorMessageFromUnknown(e, "Failed to load campaigns"));
    } finally {
      setLoadingJobs(false);
    }
  }

  function refreshAll() {
    void loadOverview();
    void loadConsumers();
    void loadJobs();
  }

  useEffect(() => {
    refreshAll();
    const timer = setInterval(() => {
      void loadJobs();
      void loadOverview();
    }, 5000);
    return () => clearInterval(timer);
  }, [clientEmailId, ready, scopeSuffix]);

  useEffect(() => {
    if (loadingOverview) return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("tab") === "schedule") {
      scheduleRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [loadingOverview]);

  function toggleDay(day: number) {
    setDaysOfWeek((current) =>
      current.includes(day)
        ? current.filter((value) => value !== day)
        : [...current, day].sort((a, b) => a - b),
    );
  }

  async function updateConsumerStatus(consumer: Consumer, newStatus: ConsumerStatusValue) {
    if (!clientEmailId) return;
    setUpdatingId(consumer.id);
    setError(null);
    setSuccess(null);
    try {
      const updated = await apiFetch<Consumer>(
        `v1/consumers/${consumer.id}?${scope}`,
        {
          method: "PUT",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ status: newStatus }),
        },
      );
      setConsumers((current) =>
        current.map((row) => (row.id === updated.id ? updated : row)),
      );
      await loadOverview();
    } catch (e) {
      setError(errorMessageFromUnknown(e, "Failed to update consumer"));
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
    if (readyCount === 0) {
      setError("Set status to Ready for at least one consumer to run a campaign.");
      return;
    }
    if (hasActiveJob) {
      setError("A campaign is already running for this client.");
      return;
    }

    setTriggering(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await apiFetch<{ job_id: string }>("v1/call-jobs/trigger", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ client_email_id: clientEmailId }),
      });
      const job = await apiFetch<CallJob>(`v1/call-jobs/${result.job_id}?${scope}`);
      setSelectedJob(job);
      setSuccess(
        `Campaign started — ${readyCount} consumer${readyCount === 1 ? "" : "s"} queued.`,
      );
      await loadJobs();
      await loadOverview();
    } catch (e) {
      setError(errorMessageFromUnknown(e, "Failed to start campaign"));
    } finally {
      setTriggering(false);
    }
  }

  async function saveSchedule(e: React.FormEvent) {
    e.preventDefault();
    if (!clientEmailId) return;
    if (daysOfWeek.length === 0) {
      setError("Select at least one day of the week.");
      return;
    }

    setSavingSchedule(true);
    setError(null);
    setSuccess(null);
    try {
      const data = await apiFetch<VoiceAgentScheduleOverview>(
        `v1/voice-agent-schedule${scopeSuffix}`,
        {
          method: "PUT",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            enabled: scheduleEnabled,
            run_time: runTime,
            days_of_week: daysOfWeek,
            timezone,
          }),
        },
      );
      setOverview(data);
      setSuccess(
        data.schedule.enabled
          ? "Schedule saved. Campaigns will run automatically at the configured time."
          : "Schedule saved. Automatic runs are disabled.",
      );
    } catch (e) {
      setError(errorMessageFromUnknown(e, "Failed to save schedule"));
    } finally {
      setSavingSchedule(false);
    }
  }

  async function viewJob(jobId: string) {
    if (!clientEmailId) return;
    try {
      const job = await apiFetch<CallJob>(`v1/call-jobs/${jobId}?${scope}`);
      setSelectedJob(job);
    } catch (e) {
      setError(errorMessageFromUnknown(e, "Failed to load campaign job"));
    }
  }

  const calcomConfigured = Boolean(
    voiceConfig?.calcom_username && voiceConfig?.calcom_event_type_slug,
  );

  return (
    <AppShell>
      <PageHeader
        title="Campaigns"
        description="Call Ready consumers now or on a schedule. Uses your voice agent settings for each outbound call."
        action={
          <Button variant="secondary" onClick={refreshAll}>
            <RefreshCw className="h-4 w-4" aria-hidden />
            Refresh
          </Button>
        }
      />

      {error ? <ErrorBanner message={error} /> : null}
      {success ? <SuccessBanner message={success} /> : null}

      {!clientEmailId ? (
        <EmptyState message="Select a client in the header to manage campaigns." />
      ) : loadingOverview && !overview ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner />
          Loading campaigns…
        </div>
      ) : (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Run campaign</CardTitle>
              <CardDescription>
                Calls all consumers with status <strong>Ready</strong> using business phone{" "}
                {clientBusinessPhoneNumber ?? "—"}.
              </CardDescription>
            </CardHeader>

            <div className="flex flex-wrap items-center gap-2">
              <Badge className="bg-muted text-foreground">
                {readyCount} ready
              </Badge>
              {scheduleEnabled ? (
                <Badge className="bg-emerald-50 text-emerald-700">
                  Schedule on · {formatScheduleDays(daysOfWeek)} {runTime}
                </Badge>
              ) : (
                <Badge className="bg-muted text-muted-foreground">Schedule off</Badge>
              )}
              {overview?.schedule.enabled && overview.schedule.next_run_at ? (
                <Badge className="bg-blue-50 text-blue-700">
                  Next: {formatDate(overview.schedule.next_run_at)}
                </Badge>
              ) : null}
              {hasActiveJob ? (
                <Badge className="bg-amber-50 text-amber-800">Running…</Badge>
              ) : null}
            </div>

            {canManageOwnConsumers ? (
              <Button
                className="mt-4"
                onClick={() => void triggerCampaign()}
                disabled={
                  triggering ||
                  !clientBusinessPhoneNumber ||
                  readyCount === 0 ||
                  hasActiveJob
                }
              >
                {triggering ? <Spinner /> : <Megaphone className="h-4 w-4" aria-hidden />}
                {triggering ? "Starting…" : `Run now (${readyCount} ready)`}
              </Button>
            ) : (
              <p className="mt-4 text-sm text-muted-foreground">
                You can view campaign progress but cannot start calls with your role.
              </p>
            )}

            <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-muted/20 px-4 py-3 text-sm">
              <div className="flex items-start gap-2">
                <Bot className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
                <div>
                  <p className="font-medium text-foreground">
                    {voiceConfig?.client_name ?? "Voice agent"}
                  </p>
                  <p className="text-muted-foreground">
                    Cal.com: {calcomConfigured ? "configured" : "not configured"}
                  </p>
                </div>
              </div>
              <Link
                href="/voice-agent"
                className="inline-flex items-center gap-1 font-medium text-primary underline-offset-4 hover:underline"
              >
                Agent settings
                <ArrowRight className="h-3.5 w-3.5" aria-hidden />
              </Link>
            </div>
          </Card>

          <div ref={scheduleRef} id="schedule" className="scroll-mt-6 max-w-2xl">
            <Card>
            <CardHeader>
              <CardTitle>Schedule</CardTitle>
              <CardDescription>
                When enabled, campaigns run automatically at the configured time for this
                client. Only <strong>Ready</strong> consumers are called.
              </CardDescription>
            </CardHeader>

            <form className="space-y-5" onSubmit={saveSchedule}>
              <label className="flex items-center gap-3 text-sm">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-input"
                  checked={scheduleEnabled}
                  disabled={!canManageOwnConsumers}
                  onChange={(e) => setScheduleEnabled(e.target.checked)}
                />
                <span>Enable automatic campaigns</span>
              </label>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <Label htmlFor="run_time">Run time</Label>
                  <Input
                    id="run_time"
                    type="time"
                    value={runTime}
                    disabled={!canManageOwnConsumers}
                    onChange={(e) => setRunTime(e.target.value)}
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="timezone">Timezone</Label>
                  <Select
                    id="timezone"
                    value={timezone}
                    disabled={!canManageOwnConsumers}
                    onChange={(e) => setTimezone(e.target.value)}
                  >
                    {TIMEZONE_OPTIONS.map((tz) => (
                      <option key={tz} value={tz}>
                        {tz}
                      </option>
                    ))}
                  </Select>
                </div>
              </div>

              <div>
                <p className="text-sm font-medium">Days of week</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {DAY_OPTIONS.map((day) => {
                    const selected = daysOfWeek.includes(day.value);
                    return (
                      <button
                        key={day.value}
                        type="button"
                        disabled={!canManageOwnConsumers}
                        onClick={() => toggleDay(day.value)}
                        className={`rounded-md border px-3 py-1.5 text-sm transition-colors ${
                          selected
                            ? "border-primary bg-primary/10 text-primary"
                            : "border-border bg-muted/30 text-muted-foreground"
                        }`}
                      >
                        {day.label}
                      </button>
                    );
                  })}
                </div>
              </div>

              <dl className="grid gap-4 rounded-lg border border-border bg-muted/20 p-4 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Next run
                  </dt>
                  <dd className="mt-1 font-medium">
                    {overview?.schedule.enabled && overview.schedule.next_run_at
                      ? formatDate(overview.schedule.next_run_at)
                      : "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Last run
                  </dt>
                  <dd className="mt-1 font-medium">
                    {overview?.schedule.last_run_at
                      ? formatDate(overview.schedule.last_run_at)
                      : "Never"}
                  </dd>
                </div>
              </dl>

              {canManageOwnConsumers ? (
                <Button type="submit" disabled={savingSchedule}>
                  {savingSchedule ? (
                    <Spinner />
                  ) : (
                    <CalendarClock className="h-4 w-4" aria-hidden />
                  )}
                  {savingSchedule ? "Saving…" : "Save schedule"}
                </Button>
              ) : (
                <p className="text-sm text-muted-foreground">
                  You can view the schedule but cannot change it with your role.
                </p>
              )}
            </form>
            </Card>
          </div>

          <Card padding={false}>
            <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border px-5 py-4 sm:px-6">
              <div>
                <CardTitle>Ready consumers</CardTitle>
                <CardDescription className="mt-1">
                  Included in the next manual or scheduled campaign. After a call, status
                  updates automatically.
                </CardDescription>
              </div>
              <Link
                href="/consumers"
                className="inline-flex shrink-0 items-center gap-1 text-sm font-medium text-primary underline-offset-4 hover:underline"
              >
                Manage all
                <ArrowRight className="h-3.5 w-3.5" aria-hidden />
              </Link>
            </div>
            <div className="p-2 sm:p-4">
              {loadingConsumers ? (
                <div className="flex items-center gap-2 px-3 py-8 text-sm text-muted-foreground">
                  <Spinner />
                  Loading consumers…
                </div>
              ) : consumers.length === 0 ? (
                <EmptyState message="No consumers yet. Add consumers on the Consumers page." />
              ) : (
                <Table>
                  <TableHead>
                    <TableHeaderCell>Phone</TableHeaderCell>
                    <TableHeaderCell>Email</TableHeaderCell>
                    <TableHeaderCell>Status</TableHeaderCell>
                  </TableHead>
                  <TableBody>
                    {consumers.map((consumer) => (
                      <TableRow key={consumer.id}>
                        <TableCell className="font-medium">
                          {consumer.consumer_phone_number}
                        </TableCell>
                        <TableCell>{consumer.consumer_email_id}</TableCell>
                        <TableCell>
                          <Select
                            aria-label={`Status for ${consumer.consumer_phone_number}`}
                            value={consumer.status}
                            disabled={!canManageOwnConsumers || updatingId === consumer.id}
                            onChange={(e) =>
                              void updateConsumerStatus(
                                consumer,
                                e.target.value as ConsumerStatusValue,
                              )
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
                      </div>
                      <div className="text-right">
                        <Badge className={statusColor(job.status)}>{job.status}</Badge>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {job.calls_completed}/{job.total_consumers} calls
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
                    {selectedJob.calls_completed} / {selectedJob.total_consumers}
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
                          key={`${result.consumer_id}-${result.consumer_phone_number}`}
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
