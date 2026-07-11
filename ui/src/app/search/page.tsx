"use client";

import { useState } from "react";
import { AppShell } from "@/components/app-shell";
import { AdminRouteGuard } from "@/components/admin-route-guard";
import {
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
  Spinner,
  SplitLayout,
} from "@/components/ui";
import { apiFetch } from "@/lib/api-client";
import { useClientScope } from "@/contexts/client-scope-context";
import type { SearchResponse } from "@/lib/types";
import { Search as SearchIcon } from "lucide-react";

export default function SearchPage() {
  const { clientEmailId, ready } = useClientScope();
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
    <AdminRouteGuard>
      <AppShell>
        <PageHeader
          title="Semantic Search"
          description="Query the selected client's knowledge base with natural language."
        />

        {error ? <ErrorBanner message={error} /> : null}

        {!clientEmailId ? (
          <EmptyState message="Select a client in the header to search." />
        ) : (
          <SplitLayout
            className="lg:grid-cols-[minmax(280px,360px)_1fr]"
            sidebar={
              <Card>
                <CardHeader>
                  <CardTitle>Search</CardTitle>
                  <CardDescription>Natural language query over indexed content.</CardDescription>
                </CardHeader>
                <form className="space-y-4" onSubmit={handleSearch}>
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
                    {loading ? (
                      <Spinner />
                    ) : (
                      <SearchIcon className="h-4 w-4" aria-hidden />
                    )}
                    {loading ? "Searching…" : "Search"}
                  </Button>
                </form>
              </Card>
            }
          >
            <Card>
              <CardHeader>
                <CardTitle>Results</CardTitle>
                {results ? (
                  <CardDescription>Collection: {results.collection}</CardDescription>
                ) : null}
              </CardHeader>
              {!results ? (
                <EmptyState message="Run a search to see matching chunks." />
              ) : results.count === 0 ? (
                <EmptyState message="No matches found." />
              ) : (
                <div className="space-y-3">
                  {results.hits.map((hit, index) => (
                    <article
                      key={`${hit.source_uri}-${index}`}
                      className="rounded-lg border border-zinc-100 bg-zinc-50/60 p-4"
                    >
                      <p className="text-sm leading-relaxed text-zinc-800">{hit.text}</p>
                      <p className="mt-2 text-xs text-zinc-500">
                        Score {hit.score.toFixed(3)}
                        {hit.source_uri ? ` · ${hit.source_uri}` : ""}
                      </p>
                    </article>
                  ))}
                </div>
              )}
            </Card>
          </SplitLayout>
        )}
      </AppShell>
    </AdminRouteGuard>
  );
}
