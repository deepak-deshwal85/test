"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Button,
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
  ErrorBanner,
  Input,
  Label,
  Select,
  Spinner,
  SuccessBanner,
} from "@/components/ui";
import { apiFetch } from "@/lib/api-client";
import type { ClientDeleteResponse, ClientProfile } from "@/lib/types";
import { AlertTriangle, Trash2 } from "lucide-react";

type DeleteClientAccountSectionProps = {
  clients: ClientProfile[];
  defaultEmail?: string | null;
  onDeleted?: (result: ClientDeleteResponse) => void | Promise<void>;
  className?: string;
};

function formatDeleteSummary(result: ClientDeleteResponse): string {
  const parts = [
    `${result.deleted_consumers} consumer${result.deleted_consumers === 1 ? "" : "s"}`,
    `${result.deleted_call_jobs} call job${result.deleted_call_jobs === 1 ? "" : "s"}`,
  ];
  if (result.qdrant_collection_deleted) {
    parts.push("knowledge base removed");
  }
  if (result.cognito_user_deleted) {
    parts.push("Cognito user removed");
  }
  return parts.join(", ");
}

export function DeleteClientAccountSection({
  clients,
  defaultEmail,
  onDeleted,
  className,
}: DeleteClientAccountSectionProps) {
  const sortedClients = useMemo(
    () =>
      [...clients].sort((a, b) =>
        a.client_email_id.localeCompare(b.client_email_id),
      ),
    [clients],
  );

  const [selectedEmail, setSelectedEmail] = useState("");
  const [confirmEmail, setConfirmEmail] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (defaultEmail && sortedClients.some((c) => c.client_email_id === defaultEmail)) {
      setSelectedEmail(defaultEmail);
      return;
    }
    if (!selectedEmail && sortedClients.length === 1) {
      setSelectedEmail(sortedClients[0].client_email_id);
    }
  }, [defaultEmail, selectedEmail, sortedClients]);

  const selectedClient = sortedClients.find(
    (client) => client.client_email_id === selectedEmail,
  );
  const confirmMatches =
    confirmEmail.trim().toLowerCase() === selectedEmail.trim().toLowerCase();

  async function handleDelete() {
    if (!selectedEmail || !confirmMatches) {
      return;
    }

    setDeleting(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await apiFetch<ClientDeleteResponse>(
        `v1/clients/account?client_email_id=${encodeURIComponent(selectedEmail)}`,
        { method: "DELETE" },
      );
      setSuccess(
        `Deleted ${result.client_email_id}: ${formatDeleteSummary(result)}.`,
      );
      setConfirmEmail("");
      setSelectedEmail("");
      await onDeleted?.(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Card className={className ?? "max-w-lg border-destructive/30"}>
      <CardHeader>
        <div className="flex items-start gap-2">
          <AlertTriangle
            className="mt-0.5 h-5 w-5 shrink-0 text-destructive"
            aria-hidden
          />
          <div>
            <CardTitle>Delete account</CardTitle>
            <CardDescription>
              Permanently remove a client and all associated data: consumers,
              call jobs, profile, knowledge base (Qdrant), and Cognito user.
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      {error ? <ErrorBanner message={error} className="mb-4" /> : null}
      {success ? <SuccessBanner message={success} className="mb-4" /> : null}

      {sortedClients.length === 0 ? (
        <p className="text-sm text-muted-foreground">No clients available to delete.</p>
      ) : (
        <div className="space-y-4">
          <div>
            <Label htmlFor="delete_client_email">Client email</Label>
            <Select
              id="delete_client_email"
              value={selectedEmail}
              onChange={(e) => {
                setSelectedEmail(e.target.value);
                setConfirmEmail("");
                setError(null);
                setSuccess(null);
              }}
            >
              <option value="">Select a client…</option>
              {sortedClients.map((client) => (
                <option key={client.id} value={client.client_email_id}>
                  {client.client_email_id}
                  {client.client_name ? ` (${client.client_name})` : ""}
                </option>
              ))}
            </Select>
          </div>

          {selectedClient ? (
            <div className="rounded-lg border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-muted-foreground">
              <p className="font-medium text-foreground">This will delete:</p>
              <ul className="mt-2 list-inside list-disc space-y-1">
                <li>Client profile for {selectedClient.client_email_id}</li>
                <li>All consumers for this client</li>
                <li>All call jobs and call history</li>
                <li>Knowledge base collection in Qdrant</li>
                <li>Cognito login for this user</li>
              </ul>
            </div>
          ) : null}

          <div>
            <Label htmlFor="delete_confirm_email">
              Type the client email to confirm
            </Label>
            <Input
              id="delete_confirm_email"
              type="email"
              autoComplete="off"
              placeholder={selectedEmail || "client@example.com"}
              value={confirmEmail}
              onChange={(e) => setConfirmEmail(e.target.value)}
              disabled={!selectedEmail}
            />
          </div>

          <Button
            type="button"
            variant="danger"
            disabled={!selectedEmail || !confirmMatches || deleting}
            onClick={() => void handleDelete()}
          >
            {deleting ? <Spinner /> : <Trash2 className="h-4 w-4" aria-hidden />}
            {deleting ? "Deleting…" : "Delete client permanently"}
          </Button>
        </div>
      )}
    </Card>
  );
}
