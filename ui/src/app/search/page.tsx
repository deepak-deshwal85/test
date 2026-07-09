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
import { useClientScope } from "@/contexts/client-scope-context";
import type { SearchResponse } from "@/lib/types";
import { Search as SearchIcon } from "lucide-react";

export default function SearchPage() {
  const { clientEmailId, clientBusinessPhoneNumber, ready } = useClientScope();
  const [query, setQuery] = useState("");
  const [maxResults, setMaxResults] = useState(5);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim() || !ready || !clientEmailId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<SearchResponse>("v1/search", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          query: query.trim(),
          phone_number: clientBusinessPhoneNumber || undefined,
          client_email_id: clientEmailId,
          max_results: maxResults,
        }),
      });
      setResults(data);
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
        description="Query the selected client's knowledge base with natural language."
      />

      {error ? <ErrorBanner message={error} /> : null}

      {!clientEmailId ? (
        <EmptyState message="Select a client in the header to search." />
      ) : (
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
      )}
    </AppShell>
  );
}
