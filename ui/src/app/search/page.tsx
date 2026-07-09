"use client";

import { useState } from "react";
import { AppShell } from "@/components/app-shell";
import {
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Input,
  Label,
  PageHeader,
} from "@/components/ui";
import { apiFetch } from "@/lib/api-client";
import { useClientProfile } from "@/hooks/use-client-profile";
import { usePermissions } from "@/hooks/use-permissions";
import type { SearchResponse } from "@/lib/types";
import { Search as SearchIcon } from "lucide-react";

export default function SearchPage() {
  const { canManageData } = usePermissions();
  const { clientEmailId, clientPhoneNumber } = useClientProfile();
  const [query, setQuery] = useState("");
  const [phone, setPhone] = useState("");
  const [maxResults, setMaxResults] = useState(5);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const effectivePhone = canManageData ? phone.trim() : (clientPhoneNumber ?? "");

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<SearchResponse>("v1/search", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          query: query.trim(),
          phone_number: effectivePhone || undefined,
          client_email_id: clientEmailId ?? undefined,
          max_results: maxResults,
        }),
      });
      setResults(data);
      if (!canManageData && data.client_phone_number) {
        setPhone(data.client_phone_number);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
      setResults(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Semantic Search"
        description="Query uploaded knowledge bases with natural language."
      />

      {error ? <ErrorBanner message={error} /> : null}

      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
        <Card>
          <form className="space-y-3" onSubmit={handleSearch}>
            <div>
              <Label htmlFor="query">Search query</Label>
              <Input
                id="query"
                required
                placeholder="What services do you offer?"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
            {canManageData ? (
              <div>
                <Label htmlFor="phone">Phone number (optional)</Label>
                <Input
                  id="phone"
                  placeholder="911171366880"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                />
              </div>
            ) : effectivePhone ? (
              <p className="text-sm text-slate-600">
                Searching collection for phone{" "}
                <span className="font-medium">{effectivePhone}</span>
              </p>
            ) : null}
            <div>
              <Label htmlFor="max">Max results</Label>
              <Input
                id="max"
                type="number"
                min={1}
                max={20}
                value={maxResults}
                onChange={(e) => setMaxResults(Number(e.target.value))}
              />
            </div>
            <Button type="submit" disabled={loading} className="w-full">
              <SearchIcon className="h-4 w-4" />
              {loading ? "Searching…" : "Search"}
            </Button>
          </form>
        </Card>

        <Card>
          <h2 className="font-semibold text-slate-900">Results</h2>
          {!results ? (
            <EmptyState message="Run a search to see matching chunks." />
          ) : results.count === 0 ? (
            <EmptyState message="No matches found." />
          ) : (
            <div className="mt-4 space-y-3">
              <p className="text-xs text-slate-500">
                Collection: {results.collection}
                {results.client_phone_number
                  ? ` · phone ${results.client_phone_number}`
                  : ""}
              </p>
              {results.hits.map((hit, index) => (
                <div
                  key={`${hit.source_uri}-${index}`}
                  className="rounded-xl border border-slate-100 bg-slate-50 p-4"
                >
                  <p className="text-sm text-slate-800">{hit.text}</p>
                  <p className="mt-2 text-xs text-slate-500">
                    score {hit.score.toFixed(3)}
                    {hit.source_uri ? ` · ${hit.source_uri}` : ""}
                  </p>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </AppShell>
  );
}
