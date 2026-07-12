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
  PageHeader,
  PageSection,
  Spinner,
  StatCard,
} from "@/components/ui";
import { apiFetch, errorMessageFromUnknown } from "@/lib/api-client";
import { clientScopeQuery, useClientScope } from "@/contexts/client-scope-context";
import { usePermissions } from "@/hooks/use-permissions";
import type {
  CallSummaryListResponse,
  CollectionListResponse,
  ConsumerListResponse,
  VoiceAgentScheduleOverview,
} from "@/lib/types";
import { formatDate } from "@/lib/utils";
import {
  ArrowRight,
  BookOpen,
  Bot,
  History,
  Megaphone,
  Search,
  Users,
} from "lucide-react";

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] as const;

function formatScheduleDays(days: number[]): string {
  if (days.length === 0) return "—";
  if (days.length === 7) return "Every day";
  if (
    days.length === 5 &&
    [1, 2, 3, 4, 5].every((day) => days.includes(day))
  ) {
    return "Mon–Fri";
  }
  return days
    .map((day) => DAY_LABELS[day - 1])
    .filter(Boolean)
    .join(", ");
}

function summaryPreview(text: string, max = 100): string {
  const trimmed = text.trim();
  if (!trimmed) return "No summary recorded.";
  if (trimmed.length <= max) return trimmed;
  return `${trimmed.slice(0, max).trim()}…`;
}

export default function DashboardPage() {
  const { canManageData } = usePermissions();
  const {
    clientEmailId,
    clientBusinessPhoneNumber,
    ready,
    selectedClient,
  } = useClientScope();

  const [overview, setOverview] = useState<VoiceAgentScheduleOverview | null>(
    null,
  );
  const [consumers, setConsumers] = useState<ConsumerListResponse | null>(
    null,
  );
  const [collections, setCollections] = useState<CollectionListResponse | null>(
    null,
  );
  const [calls, setCalls] = useState<CallSummaryListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      if (!ready || !clientEmailId) {
        setOverview(null);
        setConsumers(null);
        setCollections(null);
        setCalls(null);
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);
      const scope = clientScopeQuery(clientEmailId);

      const [overviewResult, consumerResult, collectionResult, callsResult] =
        await Promise.allSettled([
          apiFetch<VoiceAgentScheduleOverview>(`v1/voice-agent-schedule?${scope}`),
          apiFetch<ConsumerListResponse>(`v1/consumers?${scope}`),
          apiFetch<CollectionListResponse>(`v1/collections?${scope}`),
          apiFetch<CallSummaryListResponse>(`v1/call-summaries?${scope}&limit=5`),
        ]);

      const errors: string[] = [];

      if (overviewResult.status === "fulfilled") {
        setOverview(overviewResult.value);
      } else {
        errors.push(
          errorMessageFromUnknown(overviewResult.reason, "Failed to load outreach"),
        );
      }
      if (consumerResult.status === "fulfilled") {
        setConsumers(consumerResult.value);
      } else {
        errors.push(
          errorMessageFromUnknown(consumerResult.reason, "Failed to load consumers"),
        );
      }
      if (collectionResult.status === "fulfilled") {
        setCollections(collectionResult.value);
      } else {
        errors.push(
          errorMessageFromUnknown(
            collectionResult.reason,
            "Failed to load knowledge",
          ),
        );
      }
      if (callsResult.status === "fulfilled") {
        setCalls(callsResult.value);
      } else {
        errors.push(
          errorMessageFromUnknown(callsResult.reason, "Failed to load call history"),
        );
      }

      if (errors.length) setError(errors.join(" · "));
      setLoading(false);
    }

    void load();
  }, [clientEmailId, ready]);

  const readyCount = overview?.ready_consumer_count ?? 0;
  const schedule = overview?.schedule;
  const calcomConfigured = Boolean(
    overview?.voice_agent_config.calcom_username &&
      overview?.voice_agent_config.calcom_event_type_slug,
  );
  const clientLabel =
    selectedClient?.client_name ?? overview?.client_name ?? "your workspace";

  const quickActions = [
    {
      href: "/campaigns",
      label: "Campaigns",
      description: "Run or schedule outbound calls",
      icon: Megaphone,
      show: true,
    },
    {
      href: "/voice-agent",
      label: "Voice agent",
      description: "Greeting and meeting booking",
      icon: Bot,
      show: true,
    },
    {
      href: "/knowledge",
      label: "Knowledge",
      description: "Upload documents for the agent",
      icon: BookOpen,
      show: true,
    },
    {
      href: "/consumers",
      label: "Consumers",
      description: "Manage who can be called",
      icon: Users,
      show: true,
    },
    {
      href: "/search",
      label: "Search",
      description: "Test knowledge retrieval",
      icon: Search,
      show: canManageData,
    },
  ].filter((action) => action.show);

  return (
    <AppShell>
      <PageHeader
        title="Dashboard"
        description={
          clientEmailId
            ? `Overview for ${clientLabel} — outreach, calls, and knowledge at a glance.`
            : "Select a client in the header to see your workspace overview."
        }
      />

      {error ? <ErrorBanner message={error} /> : null}

      {!clientEmailId ? (
        <EmptyState message="Select a client in the header to view your dashboard." />
      ) : loading ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner />
          Loading dashboard…
        </div>
      ) : (
        <PageSection>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Ready to call"
              value={readyCount}
              icon={Megaphone}
              footer={
                <Link
                  href="/campaigns"
                  className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
                >
                  Manage campaigns
                  <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                </Link>
              }
            />
            <StatCard
              label="Consumers"
              value={consumers?.count ?? 0}
              icon={Users}
              footer={
                <Link
                  href="/consumers"
                  className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
                >
                  View all
                  <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                </Link>
              }
            />
            <StatCard
              label="Knowledge bases"
              value={collections?.count ?? 0}
              icon={BookOpen}
              footer={
                <Link
                  href="/knowledge"
                  className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
                >
                  Upload documents
                  <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                </Link>
              }
            />
            <StatCard
              label="Calls logged"
              value={calls?.count ?? 0}
              icon={History}
              footer={
                <Link
                  href="/call-history"
                  className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
                >
                  Call history
                  <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                </Link>
              }
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Outreach</CardTitle>
                <CardDescription>
                  Manual runs and automatic campaigns for Ready consumers.
                </CardDescription>
              </CardHeader>
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  <Badge className="bg-muted text-foreground">
                    {readyCount} ready
                  </Badge>
                  {schedule?.enabled ? (
                    <Badge className="bg-emerald-50 text-emerald-700">
                      Schedule on
                    </Badge>
                  ) : (
                    <Badge className="bg-muted text-muted-foreground">
                      Schedule off
                    </Badge>
                  )}
                  {overview?.has_active_job ? (
                    <Badge className="bg-amber-50 text-amber-800">
                      Campaign running
                    </Badge>
                  ) : null}
                </div>
                <dl className="grid gap-3 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Business phone
                    </dt>
                    <dd className="mt-1 font-medium">
                      {clientBusinessPhoneNumber ??
                        overview?.client_business_phone_number ??
                        "Not configured"}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Next scheduled run
                    </dt>
                    <dd className="mt-1 font-medium">
                      {schedule?.enabled && schedule.next_run_at
                        ? formatDate(schedule.next_run_at)
                        : "—"}
                    </dd>
                  </div>
                  {schedule?.enabled ? (
                    <div className="sm:col-span-2">
                      <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        Schedule
                      </dt>
                      <dd className="mt-1 font-medium">
                        {formatScheduleDays(schedule.days_of_week)} at{" "}
                        {schedule.run_time} ({schedule.timezone})
                      </dd>
                    </div>
                  ) : null}
                </dl>
                <Button asChild variant="secondary" className="w-full sm:w-auto">
                  <Link href="/campaigns">
                    <Megaphone className="h-4 w-4" aria-hidden />
                    Open campaigns
                  </Link>
                </Button>
              </div>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Voice agent</CardTitle>
                <CardDescription>
                  Settings used when your agent answers or places calls.
                </CardDescription>
              </CardHeader>
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  <Badge
                    className={
                      calcomConfigured
                        ? "bg-emerald-50 text-emerald-700"
                        : "bg-amber-50 text-amber-800"
                    }
                  >
                    Cal.com {calcomConfigured ? "ready" : "not configured"}
                  </Badge>
                  <Badge className="bg-muted text-muted-foreground">
                    {collections?.count
                      ? `${collections.count} knowledge base${collections.count === 1 ? "" : "s"}`
                      : "No documents yet"}
                  </Badge>
                </div>
                <p className="text-sm text-muted-foreground">
                  {calcomConfigured
                    ? "The agent can greet callers, search uploaded documents, and book meetings."
                    : "Add Cal.com settings so the agent can book meetings during calls."}
                </p>
                <Button asChild variant="secondary" className="w-full sm:w-auto">
                  <Link href="/voice-agent">
                    <Bot className="h-4 w-4" aria-hidden />
                    Configure agent
                  </Link>
                </Button>
              </div>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Quick actions</CardTitle>
              <CardDescription>Jump to the tasks you use most often.</CardDescription>
            </CardHeader>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {quickActions.map((action) => (
                <Link
                  key={action.href}
                  href={action.href}
                  className="flex items-start gap-3 rounded-lg border border-border bg-muted/30 px-4 py-3.5 transition-colors hover:bg-card"
                >
                  <action.icon
                    className="mt-0.5 h-4 w-4 shrink-0 text-primary"
                    aria-hidden
                  />
                  <div>
                    <p className="text-sm font-medium text-foreground">
                      {action.label}
                    </p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {action.description}
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          </Card>

          <Card>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <CardTitle>Recent calls</CardTitle>
                <CardDescription className="mt-1">
                  Latest conversations handled by your voice agent.
                </CardDescription>
              </div>
              <Link
                href="/call-history"
                className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
              >
                View all
                <ArrowRight className="h-3.5 w-3.5" aria-hidden />
              </Link>
            </div>
            <ul className="space-y-2">
              {(calls?.summaries ?? []).map((summary) => (
                <li
                  key={summary.id}
                  className="rounded-lg border border-border bg-muted/20 px-4 py-3"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="font-medium text-foreground">
                        {summary.consumer_phone_number ?? "Unknown number"}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatDate(summary.call_start_time)}
                      </p>
                    </div>
                  </div>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {summaryPreview(summary.call_summary)}
                  </p>
                </li>
              ))}
              {!calls?.summaries?.length ? (
                <li className="rounded-lg border border-dashed border-border px-4 py-8 text-center text-sm text-muted-foreground">
                  No calls yet. Run a campaign or receive an inbound call to see
                  summaries here.
                </li>
              ) : null}
            </ul>
          </Card>
        </PageSection>
      )}
    </AppShell>
  );
}
