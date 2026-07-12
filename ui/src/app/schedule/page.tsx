"use client";

import { useEffect, useState } from "react";
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
} from "@/components/ui";
import { apiFetch, errorMessageFromUnknown } from "@/lib/api-client";
import { clientScopeQuery, useClientScope } from "@/contexts/client-scope-context";
import { usePermissions } from "@/hooks/use-permissions";
import type { VoiceAgentScheduleOverview } from "@/lib/types";
import { formatDate } from "@/lib/utils";
import { CalendarClock, Megaphone, RefreshCw } from "lucide-react";

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

export default function SchedulePage() {
  const { canManageOwnConsumers } = usePermissions();
  const { clientEmailId, clientBusinessPhoneNumber, ready } = useClientScope();
  const [overview, setOverview] = useState<VoiceAgentScheduleOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [enabled, setEnabled] = useState(false);
  const [runTime, setRunTime] = useState("09:00");
  const [daysOfWeek, setDaysOfWeek] = useState<number[]>([1, 2, 3, 4, 5]);
  const [timezone, setTimezone] = useState("Asia/Kolkata");

  const scope = clientScopeQuery(clientEmailId);
  const scopeSuffix = scope ? `?${scope}` : "";

  async function loadOverview() {
    if (!ready || !clientEmailId) {
      setOverview(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<VoiceAgentScheduleOverview>(
        `v1/voice-agent-schedule${scopeSuffix}`,
      );
      setOverview(data);
      setEnabled(data.schedule.enabled);
      setRunTime(data.schedule.run_time);
      setDaysOfWeek(data.schedule.days_of_week);
      setTimezone(data.schedule.timezone);
    } catch (e) {
      setError(errorMessageFromUnknown(e, "Failed to load schedule"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadOverview();
  }, [clientEmailId, ready, scopeSuffix]);

  function toggleDay(day: number) {
    setDaysOfWeek((current) =>
      current.includes(day)
        ? current.filter((value) => value !== day)
        : [...current, day].sort((a, b) => a - b),
    );
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!clientEmailId) return;
    if (daysOfWeek.length === 0) {
      setError("Select at least one day of the week.");
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const data = await apiFetch<VoiceAgentScheduleOverview>(
        `v1/voice-agent-schedule${scopeSuffix}`,
        {
          method: "PUT",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            enabled,
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
      setSaving(false);
    }
  }

  async function runNow() {
    if (!clientEmailId) return;
    setTriggering(true);
    setError(null);
    setSuccess(null);
    try {
      await apiFetch<{ job_id: string; message: string }>(
        `v1/voice-agent-schedule/trigger${scopeSuffix}`,
        { method: "POST" },
      );
      setSuccess("Campaign started. Track progress on the Campaign page.");
      await loadOverview();
    } catch (e) {
      setError(errorMessageFromUnknown(e, "Failed to start campaign"));
    } finally {
      setTriggering(false);
    }
  }

  const config = overview?.voice_agent_config;
  const readyCount = overview?.ready_consumer_count ?? 0;

  return (
    <AppShell>
      <PageHeader
        title="Schedule voice agent"
        description="Configure automatic outbound campaigns per client. Ready consumers are called using your voice agent settings."
        action={
          <Button variant="secondary" onClick={() => void loadOverview()}>
            <RefreshCw className="h-4 w-4" aria-hidden />
            Refresh
          </Button>
        }
      />

      {error ? <ErrorBanner message={error} /> : null}
      {success ? <SuccessBanner message={success} /> : null}

      {!clientEmailId ? (
        <EmptyState message="Select a client in the header to manage the voice agent schedule." />
      ) : loading ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner />
          Loading schedule…
        </div>
      ) : (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Current voice agent configuration</CardTitle>
              <CardDescription>
                These settings are used when scheduled or manual campaigns run. Edit them on the{" "}
                <Link href="/voice-agent" className="font-medium text-primary underline-offset-4 hover:underline">
                  Voice agent
                </Link>{" "}
                page.
              </CardDescription>
            </CardHeader>
            <dl className="grid gap-4 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Business phone
                </dt>
                <dd className="mt-1 font-medium">
                  {config?.client_business_phone_number ?? clientBusinessPhoneNumber ?? "—"}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Ready consumers
                </dt>
                <dd className="mt-1 font-medium">{readyCount}</dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Greeting message
                </dt>
                <dd className="mt-1 whitespace-pre-wrap text-foreground">
                  {config?.voice_agent_greeting_message ?? "—"}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Cal.com username
                </dt>
                <dd className="mt-1">{config?.calcom_username ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Event type slug
                </dt>
                <dd className="mt-1">{config?.calcom_event_type_slug ?? "—"}</dd>
              </div>
            </dl>
          </Card>

          <Card className="max-w-2xl">
            <CardHeader>
              <CardTitle>Campaign schedule</CardTitle>
              <CardDescription>
                When enabled, the API triggers a campaign for this client at the scheduled time.
                Only consumers with status <strong>Ready</strong> are called.
              </CardDescription>
            </CardHeader>

            <form className="space-y-5" onSubmit={handleSave}>
              <label className="flex items-center gap-3 text-sm">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-input"
                  checked={enabled}
                  disabled={!canManageOwnConsumers}
                  onChange={(e) => setEnabled(e.target.checked)}
                />
                <span>Enable automatic scheduled campaigns</span>
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
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Status
                  </dt>
                  <dd className="mt-1">
                    <Badge
                      className={
                        overview?.schedule.enabled
                          ? "bg-emerald-50 text-emerald-700"
                          : "bg-muted text-muted-foreground"
                      }
                    >
                      {overview?.schedule.enabled ? "enabled" : "disabled"}
                    </Badge>
                    {overview?.has_active_job ? (
                      <span className="ml-2 text-xs text-amber-700">Campaign running</span>
                    ) : null}
                  </dd>
                </div>
              </dl>

              {canManageOwnConsumers ? (
                <div className="flex flex-wrap gap-3">
                  <Button type="submit" disabled={saving}>
                    {saving ? <Spinner /> : <CalendarClock className="h-4 w-4" aria-hidden />}
                    {saving ? "Saving…" : "Save schedule"}
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={
                      triggering ||
                      !clientBusinessPhoneNumber ||
                      readyCount === 0 ||
                      overview?.has_active_job
                    }
                    onClick={() => void runNow()}
                  >
                    {triggering ? <Spinner /> : <Megaphone className="h-4 w-4" aria-hidden />}
                    {triggering ? "Starting…" : `Run now (${readyCount} ready)`}
                  </Button>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  You can view the schedule but cannot change it with your role.
                </p>
              )}
            </form>
          </Card>
        </div>
      )}
    </AppShell>
  );
}
