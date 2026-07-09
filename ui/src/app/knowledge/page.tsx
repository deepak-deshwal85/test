"use client";

import { useEffect, useState } from "react";
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
import { apiFetch, apiUpload } from "@/lib/api-client";
import { clientScopeQuery, useClientScope } from "@/contexts/client-scope-context";
import { usePermissions } from "@/hooks/use-permissions";
import type { DocumentListResponse, DocumentSummary } from "@/lib/types";
import { Trash2, Upload } from "lucide-react";

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
        <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
          <Card>
            <h2 className="font-semibold text-slate-900">Upload</h2>
            <p className="mt-2 text-xs text-slate-500">
              Collection: <code>{collection}</code>
            </p>
            <div className="mt-4 space-y-3">
              {canUploadDocuments ? (
                <>
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
                    <Upload className="h-4 w-4" />
                    Upload
                  </Button>
                </>
              ) : (
                <p className="text-sm text-slate-600">
                  Your role can view documents but cannot upload or delete them.
                </p>
              )}
            </div>
          </Card>

          <Card>
            <h2 className="font-semibold text-slate-900">Documents</h2>
            {loading ? (
              <p className="mt-4 text-sm text-slate-500">Loading…</p>
            ) : documents.length === 0 ? (
              <EmptyState message="No documents in this collection." />
            ) : (
              <div className="mt-4 space-y-2">
                {documents.map((doc) => (
                  <div
                    key={doc.document_id}
                    className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50 px-4 py-3"
                  >
                    <div>
                      <p className="font-medium">{doc.source_uri}</p>
                      <p className="text-xs text-slate-500">
                        {doc.chunk_count} chunks · {doc.document_id}
                      </p>
                    </div>
                    {canUploadDocuments ? (
                      <Button
                        variant="ghost"
                        onClick={() => void handleDelete(doc.document_id)}
                      >
                        <Trash2 className="h-4 w-4 text-red-600" />
                      </Button>
                    ) : null}
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
