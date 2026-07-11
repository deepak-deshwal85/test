"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import {
  Button,
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
  ErrorBanner,
  Input,
  Label,
  PageHeader,
  Spinner,
  SuccessBanner,
} from "@/components/ui";
import { apiFetch } from "@/lib/api-client";
import { clientScopeQuery, useClientScope } from "@/contexts/client-scope-context";
import type { VoiceAgentConfig } from "@/lib/types";

const DEFAULT_GREETING =
  "Greet the caller briefly. Introduce the business and summarize key service offerings. Say you can answer questions by searching the uploaded documents. Ask what they would like to know.";

export default function VoiceAgentPage() {
  const { clientEmailId, selectedClient, ready } = useClientScope();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [greetingMessage, setGreetingMessage] = useState(DEFAULT_GREETING);
  const [calcomUsername, setCalcomUsername] = useState("");
  const [calcomEventSlug, setCalcomEventSlug] = useState("");
  const [calcomEventTypeId, setCalcomEventTypeId] = useState("");
  const [calcomOrgSlug, setCalcomOrgSlug] = useState("");

  const scope = clientScopeQuery(clientEmailId);
  const scopeSuffix = scope ? `?${scope}` : "";

  useEffect(() => {
    if (!ready || !clientEmailId) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    async function loadConfig() {
      setLoading(true);
      setError(null);
      try {
        const data = await apiFetch<VoiceAgentConfig>(
          `v1/voice-agent-config${scopeSuffix}`,
        );
        if (cancelled) return;
        setGreetingMessage(data.voice_agent_greeting_message || DEFAULT_GREETING);
        setCalcomUsername(data.calcom_username ?? "");
        setCalcomEventSlug(data.calcom_event_type_slug ?? "");
        setCalcomEventTypeId(
          data.calcom_event_type_id != null ? String(data.calcom_event_type_id) : "",
        );
        setCalcomOrgSlug(data.calcom_organization_slug ?? "");
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Failed to load voice agent settings");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void loadConfig();
    return () => {
      cancelled = true;
    };
  }, [clientEmailId, ready, scopeSuffix]);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!clientEmailId) {
      setError("Select a client before saving voice agent settings.");
      return;
    }

    setSaving(true);
    setError(null);
    setSuccess(null);

    const parsedEventTypeId = calcomEventTypeId.trim()
      ? Number.parseInt(calcomEventTypeId.trim(), 10)
      : null;

    if (calcomEventTypeId.trim() && Number.isNaN(parsedEventTypeId)) {
      setError("Cal.com event type ID must be a number.");
      setSaving(false);
      return;
    }

    try {
      await apiFetch<VoiceAgentConfig>(`v1/voice-agent-config${scopeSuffix}`, {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          voice_agent_greeting_message: greetingMessage.trim(),
          calcom_username: calcomUsername.trim() || null,
          calcom_event_type_slug: calcomEventSlug.trim() || null,
          calcom_event_type_id: parsedEventTypeId,
          calcom_organization_slug: calcomOrgSlug.trim() || null,
        }),
      });
      setSuccess("Voice agent settings saved. Changes apply on the next call.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save voice agent settings");
    } finally {
      setSaving(false);
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Voice agent"
        description="Configure how your AI phone agent greets callers and books meetings. Factual answers come from uploaded documents when callers ask questions."
      />

      <div className="space-y-6">
        {error ? <ErrorBanner message={error} /> : null}
        {success ? <SuccessBanner message={success} /> : null}

        <Card className="max-w-2xl">
          <CardHeader>
            <CardTitle>Client</CardTitle>
            <CardDescription>
              Settings apply to calls routed to your business phone number.
            </CardDescription>
          </CardHeader>
          <dl className="grid gap-4 text-sm sm:grid-cols-2">
            <div>
              <dt className="font-medium text-muted-foreground">Business phone</dt>
              <dd className="mt-1 text-foreground">
                {selectedClient?.client_business_phone_number ?? "—"}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-muted-foreground">Client name</dt>
              <dd className="mt-1 text-foreground">
                {selectedClient?.client_name ?? "—"}
              </dd>
            </div>
          </dl>
        </Card>

        <Card className="max-w-2xl">
          <CardHeader>
            <CardTitle>Voice agent settings</CardTitle>
            <CardDescription>
              These values are loaded by the voice agent at the start of each call.
            </CardDescription>
          </CardHeader>

          {loading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Spinner />
              Loading settings…
            </div>
          ) : (
            <form className="space-y-5" onSubmit={handleSave}>
              <div>
                <Label htmlFor="greeting_message">Greeting message</Label>
                <textarea
                  id="greeting_message"
                  required
                  rows={6}
                  className="mt-1.5 flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  value={greetingMessage}
                  onChange={(e) => setGreetingMessage(e.target.value)}
                  placeholder={DEFAULT_GREETING}
                />
                <p className="mt-1.5 text-xs text-muted-foreground">
                  Instructions for the opening greeting. Include your business name, service
                  offerings, and that you can answer questions from uploaded documents.
                </p>
              </div>

              <div className="border-t pt-5">
                <h3 className="text-sm font-medium text-foreground">Cal.com scheduling</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  Required for meeting booking during calls. Leave blank to disable scheduling tools.
                </p>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <Label htmlFor="calcom_username">Cal.com username</Label>
                  <Input
                    id="calcom_username"
                    value={calcomUsername}
                    onChange={(e) => setCalcomUsername(e.target.value)}
                    placeholder="your-calcom-username"
                  />
                </div>
                <div>
                  <Label htmlFor="calcom_event_slug">Event type slug</Label>
                  <Input
                    id="calcom_event_slug"
                    value={calcomEventSlug}
                    onChange={(e) => setCalcomEventSlug(e.target.value)}
                    placeholder="30min"
                  />
                </div>
                <div>
                  <Label htmlFor="calcom_event_type_id">Event type ID (optional)</Label>
                  <Input
                    id="calcom_event_type_id"
                    inputMode="numeric"
                    value={calcomEventTypeId}
                    onChange={(e) => setCalcomEventTypeId(e.target.value)}
                    placeholder="6073963"
                  />
                </div>
                <div>
                  <Label htmlFor="calcom_org_slug">Organization slug (optional)</Label>
                  <Input
                    id="calcom_org_slug"
                    value={calcomOrgSlug}
                    onChange={(e) => setCalcomOrgSlug(e.target.value)}
                  />
                </div>
              </div>

              <Button type="submit" disabled={saving || !clientEmailId}>
                {saving ? <Spinner /> : null}
                {saving ? "Saving…" : "Save settings"}
              </Button>
            </form>
          )}
        </Card>
      </div>
    </AppShell>
  );
}
