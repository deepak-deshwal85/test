"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { AdminRouteGuard } from "@/components/admin-route-guard";
import {
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  PageHeader,
  Spinner,
} from "@/components/ui";
import { apiFetch } from "@/lib/api-client";
import { clientScopeQuery, useClientScope } from "@/contexts/client-scope-context";
import { usePermissions } from "@/hooks/use-permissions";
import type { CollectionInfo, CollectionListResponse } from "@/lib/types";
import { Database, RefreshCw, Trash2 } from "lucide-react";

export default function CollectionsPage() {
  const { canManageData } = usePermissions();
  const { clientEmailId, ready } = useClientScope();
  const [collections, setCollections] = useState<string[]>([]);
  const [details, setDetails] = useState<Record<string, CollectionInfo>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const scopeSuffix = (() => {
    const scope = clientScopeQuery(clientEmailId);
    return scope ? `?${scope}` : "";
  })();

  async function load() {
    if (!canManageData && !ready) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<CollectionListResponse>(
        `v1/collections${scopeSuffix}`,
      );
      setCollections(data.collections);
      const infoEntries = await Promise.all(
        data.collections.map(async (name) => {
          const info = await apiFetch<CollectionInfo>(
            `v1/collections/${encodeURIComponent(name)}${scopeSuffix}`,
          );
          return [name, info] as const;
        }),
      );
      setDetails(Object.fromEntries(infoEntries));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load collections");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!ready) return;
    void load();
  }, [clientEmailId, ready]);

  async function handleDelete(name: string) {
    if (!confirm(`Delete collection ${name}? This cannot be undone.`)) return;
    try {
      await apiFetch(`v1/collections/${encodeURIComponent(name)}${scopeSuffix}`, {
        method: "DELETE",
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  return (
    <AdminRouteGuard>
      <AppShell>
        <PageHeader
          title="Collections"
          description="Browse and manage Qdrant vector collections."
          action={
            <Button variant="secondary" onClick={() => void load()}>
              <RefreshCw className="h-4 w-4" aria-hidden />
              Refresh
            </Button>
          }
        />

        {error ? <ErrorBanner message={error} /> : null}

        <Card>
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-zinc-500">
              <Spinner />
              Loading collections…
            </div>
          ) : collections.length === 0 ? (
            <EmptyState message="No collections yet. Upload documents to create one." />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {collections.map((name) => {
                const info = details[name];
                return (
                  <div
                    key={name}
                    className="rounded-lg border border-zinc-200 bg-zinc-50/40 p-4 transition-colors hover:bg-white"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <Database
                            className="h-4 w-4 shrink-0 text-brand-600"
                            aria-hidden
                          />
                          <p className="truncate font-semibold text-zinc-900">
                            {name}
                          </p>
                        </div>
                        <p className="mt-3 text-sm text-zinc-600">
                          {info?.points_count ?? 0} points
                        </p>
                        <p className="text-xs text-zinc-500">
                          Vector size {info?.vector_size ?? "—"}
                        </p>
                      </div>
                      {canManageData ? (
                        <Button
                          variant="ghost"
                          size="icon"
                          aria-label={`Delete ${name}`}
                          onClick={() => void handleDelete(name)}
                        >
                          <Trash2 className="h-4 w-4 text-red-600" aria-hidden />
                        </Button>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      </AppShell>
    </AdminRouteGuard>
  );
}
