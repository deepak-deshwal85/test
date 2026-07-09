"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { Badge, Card, PageHeader } from "@/components/ui";
import { apiFetch, errorMessageFromUnknown } from "@/lib/api-client";
import { clientScopeQuery, useClientProfile } from "@/hooks/use-client-profile";
import { usePermissions } from "@/hooks/use-permissions";
import type {
  CollectionListResponse,
  CustomerListResponse,
  HealthResponse,
} from "@/lib/types";
import { BookOpen, PhoneCall, Users } from "lucide-react";

export default function DashboardPage() {
  const { canManageData } = usePermissions();
  const { clientEmailId, ready } = useClientProfile();
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

        if (!ready) return;

        const scope = clientScopeQuery(clientEmailId);
        const customerPath = scope
          ? `v1/customers?limit=5&${scope}`
          : "v1/customers?limit=5";
        const collectionPath = scope ? `v1/collections?${scope}` : "v1/collections";

        const [customerResult, collectionResult] = await Promise.allSettled([
          apiFetch<CustomerListResponse>(customerPath),
          apiFetch<CollectionListResponse>(collectionPath),
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
        if (errors.length) {
          setError(errors.join(" · "));
        }
      } catch (e) {
        setError(errorMessageFromUnknown(e, "Failed to load dashboard"));
      }
    }

    void load();
  }, [canManageData, clientEmailId, ready]);

  return (
    <AppShell>
      <PageHeader
        title="Dashboard"
        description="Overview of customers, knowledge bases, and platform health."
      />

      {error ? (
        <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <Card>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-slate-500">API status</p>
              <p className="mt-2 text-2xl font-semibold capitalize">
                {health?.status ?? "unknown"}
              </p>
            </div>
            <Badge
              className={
                health?.status === "ok"
                  ? "bg-emerald-100 text-emerald-800"
                  : "bg-amber-100 text-amber-800"
              }
            >
              live
            </Badge>
          </div>
        </Card>

        <Card>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-slate-500">Customers</p>
              <p className="mt-2 text-2xl font-semibold">
                {customers?.count ?? 0}
              </p>
            </div>
            <Users className="h-5 w-5 text-brand-600" />
          </div>
          <Link
            href="/customers"
            className="mt-4 inline-block text-sm font-medium text-brand-600"
          >
            Manage customers →
          </Link>
        </Card>

        <Card>
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-slate-500">Knowledge collections</p>
              <p className="mt-2 text-2xl font-semibold">
                {collections?.count ?? 0}
              </p>
            </div>
            <BookOpen className="h-5 w-5 text-brand-600" />
          </div>
          <Link
            href="/knowledge"
            className="mt-4 inline-block text-sm font-medium text-brand-600"
          >
            Upload documents →
          </Link>
        </Card>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card>
          <h3 className="font-semibold text-slate-900">Quick actions</h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <Link
              href="/call-jobs"
              className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium hover:bg-white"
            >
              <PhoneCall className="h-4 w-4 text-brand-600" />
              Trigger outbound calls
            </Link>
            <Link
              href="/search"
              className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm font-medium hover:bg-white"
            >
              <BookOpen className="h-4 w-4 text-brand-600" />
              Search knowledge base
            </Link>
          </div>
        </Card>

        <Card>
          <h3 className="font-semibold text-slate-900">Recent customers</h3>
          <ul className="mt-4 space-y-3">
            {(customers?.customers ?? []).map((customer) => (
              <li
                key={customer.id}
                className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 text-sm"
              >
                <div>
                  <p className="font-medium">{customer.client_name}</p>
                  <p className="text-slate-500">{customer.consumer_phone_number}</p>
                </div>
                <span className="text-xs text-slate-400">
                  {customer.client_phone_number}
                </span>
              </li>
            ))}
            {!customers?.customers?.length ? (
              <li className="text-sm text-slate-500">No customers yet.</li>
            ) : null}
          </ul>
        </Card>
      </div>
    </AppShell>
  );
}
