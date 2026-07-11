"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import {
  AlertBanner,
  Badge,
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
  PageHeader,
  PageSection,
  StatCard,
} from "@/components/ui";
import { apiFetch, errorMessageFromUnknown } from "@/lib/api-client";
import { clientScopeQuery, useClientScope } from "@/contexts/client-scope-context";
import type {
  CollectionListResponse,
  CustomerListResponse,
  HealthResponse,
} from "@/lib/types";
import { ArrowRight, BookOpen, Megaphone, Users } from "lucide-react";
import { callScheduleLabel, customerStatusColor, customerStatusLabel } from "@/lib/utils";

export default function DashboardPage() {
  const { clientEmailId, ready } = useClientScope();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [customers, setCustomers] = useState<CustomerListResponse | null>(null);
  const [collections, setCollections] = useState<CollectionListResponse | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setError(null);
      try {
        const healthData = await apiFetch<HealthResponse>("health");
        setHealth(healthData);

        if (!ready || !clientEmailId) return;

        const scope = clientScopeQuery(clientEmailId);
        const [customerResult, collectionResult] = await Promise.allSettled([
          apiFetch<CustomerListResponse>(`v1/customers?limit=5&${scope}`),
          apiFetch<CollectionListResponse>(`v1/collections?${scope}`),
        ]);

        const errors: string[] = [];
        if (customerResult.status === "fulfilled") {
          setCustomers(customerResult.value);
        } else {
          errors.push(
            errorMessageFromUnknown(customerResult.reason, "Failed to load customers"),
          );
        }
        if (collectionResult.status === "fulfilled") {
          setCollections(collectionResult.value);
        } else {
          errors.push(
            errorMessageFromUnknown(
              collectionResult.reason,
              "Failed to load collections",
            ),
          );
        }
        if (errors.length) setError(errors.join(" · "));
      } catch (e) {
        setError(errorMessageFromUnknown(e, "Failed to load dashboard"));
      }
    }

    void load();
  }, [clientEmailId, ready]);

  return (
    <AppShell>
      <PageHeader
        title="Dashboard"
        description="Overview of customers, knowledge bases, and platform health."
      />

      {error ? <AlertBanner message={error} /> : null}

      <PageSection>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <StatCard
            label="API status"
            value={
              <span className="capitalize">{health?.status ?? "unknown"}</span>
            }
            badge={
              <Badge
                className={
                  health?.status === "ok"
                    ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200"
                    : "bg-amber-50 text-amber-700 ring-1 ring-amber-200"
                }
              >
                live
              </Badge>
            }
          />

          <StatCard
            label="Customers"
            value={customers?.count ?? 0}
            icon={Users}
            footer={
              <Link
                href="/customers"
                className="inline-flex items-center gap-1 text-sm font-medium text-brand-600 hover:text-brand-700"
              >
                Manage customers
                <ArrowRight className="h-3.5 w-3.5" aria-hidden />
              </Link>
            }
          />

          <StatCard
            label="Knowledge collections"
            value={collections?.count ?? 0}
            icon={BookOpen}
            footer={
              <Link
                href="/knowledge"
                className="inline-flex items-center gap-1 text-sm font-medium text-brand-600 hover:text-brand-700"
              >
                Upload documents
                <ArrowRight className="h-3.5 w-3.5" aria-hidden />
              </Link>
            }
          />
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Quick actions</CardTitle>
              <CardDescription>Common workflows for your workspace.</CardDescription>
            </CardHeader>
            <div className="grid gap-3 sm:grid-cols-2">
              <Link
                href="/campaigns"
                className="flex items-center gap-3 rounded-lg border border-zinc-200 bg-zinc-50 px-4 py-3.5 text-sm font-medium text-zinc-800 transition-colors hover:border-zinc-300 hover:bg-white"
              >
                <Megaphone className="h-4 w-4 text-brand-600" aria-hidden />
                Manage campaign
              </Link>
              <Link
                href="/search"
                className="flex items-center gap-3 rounded-lg border border-zinc-200 bg-zinc-50 px-4 py-3.5 text-sm font-medium text-zinc-800 transition-colors hover:border-zinc-300 hover:bg-white"
              >
                <BookOpen className="h-4 w-4 text-brand-600" aria-hidden />
                Search knowledge base
              </Link>
            </div>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent customers</CardTitle>
              <CardDescription>Latest consumers for the active client.</CardDescription>
            </CardHeader>
            <ul className="space-y-2">
              {(customers?.customers ?? []).map((customer) => (
                <li
                  key={customer.id}
                  className="flex items-center justify-between rounded-lg border border-zinc-100 bg-zinc-50/80 px-3 py-2.5 text-sm"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium text-zinc-900">
                      {customer.consumer_phone_number}
                    </p>
                    <p className="truncate text-xs text-zinc-500">
                      {customer.consumer_email_id}
                    </p>
                  </div>
                  <Badge className={customerStatusColor(customer.status)}>
                    {customerStatusLabel(customer.status)}
                  </Badge>
                </li>
              ))}
              {!customers?.customers?.length ? (
                <li className="text-sm text-zinc-500">No customers yet.</li>
              ) : null}
            </ul>
          </Card>
        </div>
      </PageSection>
    </AppShell>
  );
}
