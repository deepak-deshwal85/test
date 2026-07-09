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
import { clientScopeQuery, useClientProfile } from "@/hooks/use-client-profile";
import { usePermissions } from "@/hooks/use-permissions";
import type {
  CollectionListResponse,
  DocumentListResponse,
  DocumentSummary,
} from "@/lib/types";
import { Trash2, Upload } from "lucide-react";

function phoneToCollection(phone: string): string {
  const digits = phone.replace(/\D/g, "");
  return `phone_${digits}`;
}

export default function KnowledgePage() {
  const { canUploadDocuments, canManageData } = usePermissions();
  const { clientEmailId, clientPhoneNumber, collectionName } = useClientProfile();
  const [collections, setCollections] = useState<string[]>([]);
  const [phone, setPhone] = useState("");
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const scope = clientScopeQuery(clientEmailId);
  const scopeSuffix = scope ? `?${scope}` : "";

  useEffect(() => {
    if (clientPhoneNumber && !canManageData) {
      setPhone(clientPhoneNumber);
    }
  }, [canManageData, clientPhoneNumber]);

  async function loadCollections() {
    try {
      const data = await apiFetch<CollectionListResponse>(
        `v1/collections${scopeSuffix}`,
      );
      setCollections(data.collections);
      if (!canManageData && data.client_phone_number) {
        setPhone(data.client_phone_number);
      }
    } catch {
      /* optional */
    }
  }

  async function loadDocuments(collection: string) {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<DocumentListResponse>(
        `v1/collections/${encodeURIComponent(collection)}/documents${scopeSuffix}`,
      );
      setDocuments(data.documents);
      if (!canManageData && data.client_phone_number) {
        setPhone(data.client_phone_number);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load documents");
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadCollections();
  }, [clientEmailId]);

  const collection =
    !canManageData && collectionName
      ? collectionName
      : phone
        ? phoneToCollection(phone)
        : "";

  useEffect(() => {
    if (collection) {
      void loadDocuments(collection);
    }
  }, [collection, clientEmailId]);

  async function handleUpload() {
    if (!collection || !file) {
      setError("Select a phone number and file to upload.");
      return;
    }
    setError(null);
    try {
      await apiUpload(
        `v1/collections/${encodeURIComponent(collection)}/documents/upload${scopeSuffix}`,
        file,
      );
      setFile(null);
      await loadDocuments(collection);
      await loadCollections();
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
      await loadDocuments(collection);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Knowledge Base"
        description="Upload PDF, Markdown, or text files per client phone collection."
      />

      {error ? <ErrorBanner message={error} /> : null}

      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
        <Card>
          <h2 className="font-semibold text-slate-900">Collection</h2>
          <div className="mt-4 space-y-3">
            <div>
              <Label htmlFor="phone">Client phone number</Label>
              <Input
                id="phone"
                list="collections-list"
                placeholder="911171366880"
                value={phone}
                disabled={!canManageData}
                onChange={(e) => setPhone(e.target.value)}
              />
              <datalist id="collections-list">
                {collections.map((name) => (
                  <option key={name} value={name.replace(/^phone_/, "")} />
                ))}
              </datalist>
            </div>
            {collection ? (
              <p className="text-xs text-slate-500">
                Collection: <code>{collection}</code>
              </p>
            ) : null}
            {canManageData ? (
              <Button
                variant="secondary"
                className="w-full"
                onClick={() => collection && void loadDocuments(collection)}
              >
                Load documents
              </Button>
            ) : null}

            <div className="border-t border-slate-100 pt-4">
              {canUploadDocuments ? (
                <>
                  <Label htmlFor="file">Upload document</Label>
                  <Input
                    id="file"
                    type="file"
                    accept=".pdf,.txt,.md"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  />
                  <Button
                    className="mt-3 w-full"
                    onClick={() => void handleUpload()}
                    disabled={!file || !collection}
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
          </div>
        </Card>

        <Card>
          <h2 className="font-semibold text-slate-900">Documents</h2>
          {loading ? (
            <p className="mt-4 text-sm text-slate-500">Loading…</p>
          ) : !collection ? (
            <EmptyState message="Enter a phone number to view documents." />
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
    </AppShell>
  );
}
