"use client";

import { useEffect, useState } from "react";
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
  Label,
  PageHeader,
  Spinner,
  SplitLayout,
} from "@/components/ui";
import { apiFetch, apiUpload } from "@/lib/api-client";
import { clientScopeQuery, useClientScope } from "@/contexts/client-scope-context";
import { usePermissions } from "@/hooks/use-permissions";
import type { DocumentListResponse, DocumentSummary } from "@/lib/types";
import { FileText, Trash2, Upload } from "lucide-react";

export default function KnowledgePage() {
  const { canUploadDocuments } = usePermissions();
  const { clientEmailId, collectionName, ready } = useClientScope();
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const scope = clientScopeQuery(clientEmailId);
  const scopeSuffix = scope ? `?${scope}` : "";
  const collection = collectionName ?? "";

  async function loadDocuments() {
    if (!collection || !ready) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<DocumentListResponse>(
        `v1/collections/${encodeURIComponent(collection)}/documents${scopeSuffix}`,
      );
      setDocuments(data.documents);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load documents");
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadDocuments();
  }, [collection, clientEmailId, ready]);

  async function handleUpload() {
    if (!collection || !file) {
      setError("Select a client with a business phone and choose a file.");
      return;
    }
    setError(null);
    try {
      await apiUpload(
        `v1/collections/${encodeURIComponent(collection)}/documents/upload${scopeSuffix}`,
        file,
      );
      setFile(null);
      await loadDocuments();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    }
  }

  async function handleDelete(documentId: string) {
    if (!collection || !confirm("Delete this document?")) return;
    try {
      await apiFetch(
        `v1/collections/${encodeURIComponent(collection)}/documents/${encodeURIComponent(documentId)}${scopeSuffix}`,
        { method: "DELETE" },
      );
      await loadDocuments();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Knowledge Base"
        description="Upload PDF, Markdown, or text files for the selected client."
      />

      {error ? <ErrorBanner message={error} /> : null}

      {!clientEmailId || !collection ? (
        <EmptyState message="Select a client with a business phone in the header." />
      ) : (
        <SplitLayout
          sidebar={
            <Card>
              <CardHeader>
                <CardTitle>Upload document</CardTitle>
                <CardDescription>
                  Collection{" "}
                  <code className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-700">
                    {collection}
                  </code>
                </CardDescription>
              </CardHeader>
              {canUploadDocuments ? (
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="file">Document</Label>
                    <Input
                      id="file"
                      type="file"
                      accept=".pdf,.txt,.md"
                      onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                    />
                  </div>
                  <Button
                    className="w-full"
                    onClick={() => void handleUpload()}
                    disabled={!file}
                  >
                    <Upload className="h-4 w-4" aria-hidden />
                    Upload
                  </Button>
                </div>
              ) : (
                <p className="text-sm text-zinc-500">
                  Your role can view documents but cannot upload or delete them.
                </p>
              )}
            </Card>
          }
        >
          <Card>
            <CardHeader>
              <CardTitle>Documents</CardTitle>
              <CardDescription>
                Indexed chunks available for semantic search.
              </CardDescription>
            </CardHeader>
            {loading ? (
              <div className="flex items-center gap-2 text-sm text-zinc-500">
                <Spinner />
                Loading documents…
              </div>
            ) : documents.length === 0 ? (
              <EmptyState message="No documents in this collection." />
            ) : (
              <div className="space-y-2">
                {documents.map((doc) => (
                  <div
                    key={doc.document_id}
                    className="flex items-center justify-between gap-3 rounded-lg border border-zinc-100 bg-zinc-50/50 px-4 py-3 transition-colors hover:bg-white"
                  >
                    <div className="flex min-w-0 items-start gap-3">
                      <FileText
                        className="mt-0.5 h-4 w-4 shrink-0 text-brand-600"
                        aria-hidden
                      />
                      <div className="min-w-0">
                        <p className="truncate font-medium text-zinc-900">
                          {doc.source_uri}
                        </p>
                        <p className="mt-0.5 text-xs text-zinc-500">
                          {doc.chunk_count} chunks · {doc.document_id}
                        </p>
                      </div>
                    </div>
                    {canUploadDocuments ? (
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Delete document"
                        onClick={() => void handleDelete(doc.document_id)}
                      >
                        <Trash2 className="h-4 w-4 text-red-600" aria-hidden />
                      </Button>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </SplitLayout>
      )}
    </AppShell>
  );
}
