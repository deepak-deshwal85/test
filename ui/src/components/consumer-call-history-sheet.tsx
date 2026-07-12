"use client";

import { useEffect, useState } from "react";
import {
  EmptyState,
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  Spinner,
} from "@/components/ui";
import { apiFetch } from "@/lib/api-client";
import { clientScopeQuery } from "@/contexts/client-scope-context";
import type { CallSummary, CallSummaryListResponse } from "@/lib/types";
import { formatDate } from "@/lib/utils";

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

type ConsumerCallHistorySheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  clientEmailId: string | null;
  consumerId: number | null;
  consumerPhone?: string;
  consumerEmail?: string;
};

export function ConsumerCallHistorySheet({
  open,
  onOpenChange,
  clientEmailId,
  consumerId,
  consumerPhone,
  consumerEmail,
}: ConsumerCallHistorySheetProps) {
  const [summaries, setSummaries] = useState<CallSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !clientEmailId || !consumerId) {
      return;
    }
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const scope = clientScopeQuery(clientEmailId!);
        const data = await apiFetch<CallSummaryListResponse>(
          `v1/call-summaries?${scope}&consumer_id=${consumerId}&limit=50`,
        );
        if (!cancelled) {
          setSummaries(data.summaries);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load call history");
          setSummaries([]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [open, clientEmailId, consumerId]);

  const title = consumerPhone ?? (consumerId ? `Consumer #${consumerId}` : "Call history");

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>{title}</SheetTitle>
          <SheetDescription>
            {consumerEmail ? `${consumerEmail} · ` : ""}
            Past call summaries for this consumer
          </SheetDescription>
        </SheetHeader>
        <div className="mt-4 space-y-4 overflow-y-auto px-1 pb-6">
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Spinner />
              Loading…
            </div>
          ) : error ? (
            <p className="text-sm text-red-600">{error}</p>
          ) : summaries.length === 0 ? (
            <EmptyState message="No calls recorded for this consumer yet." />
          ) : (
            summaries.map((item) => (
              <article
                key={item.id}
                className="rounded-lg border border-border bg-card p-4 shadow-sm"
              >
                <div className="mb-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                  <time dateTime={item.call_start_time}>
                    {formatDate(item.call_start_time)}
                  </time>
                  <span aria-hidden>·</span>
                  <span>
                    {formatDuration(item.call_start_time, item.call_end_time)}
                  </span>
                </div>
                <p className="text-sm leading-relaxed whitespace-pre-wrap">
                  {item.call_summary}
                </p>
              </article>
            ))
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
