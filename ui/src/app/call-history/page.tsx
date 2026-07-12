"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import {
  Button,
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
  EmptyState,
  ErrorBanner,
  Input,
  PageHeader,
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  Spinner,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeaderCell,
  TableRow,
} from "@/components/ui";
import { apiFetch } from "@/lib/api-client";
import { clientScopeQuery, useClientScope } from "@/contexts/client-scope-context";
import type { CallSummary, CallSummaryListResponse } from "@/lib/types";
import { formatDate } from "@/lib/utils";
import { History, RefreshCw } from "lucide-react";

function formatDuration(start: string, end: string | null): string {
  if (!end) return "—";
  const seconds = Math.max(
    0,
    Math.round((new Date(end).getTime() - new Date(start).getTime()) / 1000),
  );
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return remainder ? `${minutes}m ${remainder}s` : `${minutes}m`;
}

function summaryPreview(text: string, max = 120): string {
  const trimmed = text.trim();
  if (trimmed.length <= max) return trimmed;
  return `${trimmed.slice(0, max).trim()}…`;
}

export default function CallHistoryPage() {
  const { clientEmailId, ready } = useClientScope();
  const [summaries, setSummaries] = useState<CallSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<CallSummary | null>(null);

  async function load() {
    if (!ready || !clientEmailId) {
      setSummaries([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const scope = clientScopeQuery(clientEmailId);
      const data = await apiFetch<CallSummaryListResponse>(
        `v1/call-summaries?${scope}&limit=200`,
      );
      setSummaries(data.summaries);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load call history");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [clientEmailId, ready]);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return summaries;
    return summaries.filter((item) => {
      const haystack = [
        item.consumer_phone_number,
        item.consumer_email_id,
        item.call_summary,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(query);
    });
  }, [search, summaries]);

  return (
    <AppShell>
      <PageHeader
        title="Call history"
        description="Review transcripts and notes from completed voice calls."
        action={
          <Button onClick={() => void load()} variant="secondary">
            <RefreshCw className="h-4 w-4" aria-hidden />
            Refresh
          </Button>
        }
      />

      {error ? <ErrorBanner message={error} /> : null}

      {!clientEmailId ? (
        <EmptyState message="Select a client in the header to view call history." />
      ) : (
        <Card padding={false}>
          <div className="border-b border-border px-5 py-4 sm:px-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <History className="h-5 w-5 text-muted-foreground" aria-hidden />
                  All calls
                </CardTitle>
                <CardDescription className="mt-1">
                  {filtered.length} record{filtered.length === 1 ? "" : "s"}
                </CardDescription>
              </div>
              <Input
                aria-label="Search call history"
                placeholder="Search phone, email, or summary…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="sm:max-w-xs"
              />
            </div>
          </div>
          <div className="p-2 sm:p-4">
            {loading ? (
              <div className="flex items-center gap-2 px-3 py-8 text-sm text-muted-foreground">
                <Spinner />
                Loading call history…
              </div>
            ) : filtered.length === 0 ? (
              <EmptyState message="No call summaries yet. Summaries appear after outbound campaign calls complete." />
            ) : (
              <Table>
                <TableHead>
                  <TableHeaderCell>Consumer</TableHeaderCell>
                  <TableHeaderCell>Started</TableHeaderCell>
                  <TableHeaderCell>Duration</TableHeaderCell>
                  <TableHeaderCell>Summary</TableHeaderCell>
                </TableHead>
                <TableBody>
                  {filtered.map((item) => (
                    <TableRow
                      key={item.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => setSelected(item)}
                    >
                      <TableCell>
                        <div className="font-medium">
                          {item.consumer_phone_number ?? `#${item.consumer_id}`}
                        </div>
                        {item.consumer_email_id ? (
                          <div className="text-xs text-muted-foreground">
                            {item.consumer_email_id}
                          </div>
                        ) : null}
                      </TableCell>
                      <TableCell>{formatDate(item.call_start_time)}</TableCell>
                      <TableCell>
                        {formatDuration(item.call_start_time, item.call_end_time)}
                      </TableCell>
                      <TableCell className="max-w-md text-muted-foreground">
                        {summaryPreview(item.call_summary)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </Card>
      )}

      <Sheet open={selected !== null} onOpenChange={(open) => !open && setSelected(null)}>
        <SheetContent side="right" className="w-full sm:max-w-lg">
          {selected ? (
            <>
              <SheetHeader>
                <SheetTitle>
                  {selected.consumer_phone_number ?? `Consumer #${selected.consumer_id}`}
                </SheetTitle>
                <SheetDescription>
                  {formatDate(selected.call_start_time)}
                  {" · "}
                  {formatDuration(selected.call_start_time, selected.call_end_time)}
                </SheetDescription>
              </SheetHeader>
              <div className="mt-4 space-y-4 overflow-y-auto px-1 pb-6">
                {selected.consumer_email_id ? (
                  <p className="text-sm text-muted-foreground">
                    {selected.consumer_email_id}
                  </p>
                ) : null}
                <div className="rounded-lg border border-border bg-muted/30 p-4 text-sm leading-relaxed whitespace-pre-wrap">
                  {selected.call_summary}
                </div>
                <Button variant="secondary" asChild>
                  <Link href={`/consumers?consumer=${selected.consumer_id}`}>
                    View consumer
                  </Link>
                </Button>
              </div>
            </>
          ) : null}
        </SheetContent>
      </Sheet>
    </AppShell>
  );
}
