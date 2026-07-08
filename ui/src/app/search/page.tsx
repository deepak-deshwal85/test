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
import type { SearchResponse } from "@/lib/types";
import { Search as SearchIcon } from "lucide-react";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [phone, setPhone] = useState("");
  const [maxResults, setMaxResults] = useState(5);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
          phone_number: phone.trim() || undefined,
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
            <div>
              <Label htmlFor="phone">Phone number (optional)</Label>
              <Input
                id="phone"
                placeholder="911171366880"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
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
          ) : (
            <div className="mt-4 space-y-3">
              <p className="text-sm text-slate-500">
                Collection <code>{results.collection}</code> · {results.count}{" "}
                hits
              </p>
              {results.hits.map((hit, index) => (
                <div
                  key={`${hit.source_uri}-${index}`}
                  className="rounded-xl border border-slate-100 bg-slate-50 p-4"
                >
                  <div className="mb-2 flex items-center justify-between text-xs text-slate-500">
                    <span>{hit.source_uri ?? "unknown source"}</span>
                    <span>score {(hit.score * 100).toFixed(1)}%</span>
                  </div>
                  <p className="text-sm leading-relaxed text-slate-800">
                    {hit.text}
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
