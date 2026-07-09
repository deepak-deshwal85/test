"use client";

import { useCallback, useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { apiFetch } from "@/lib/api-client";
import { isAuthDisabledForLocal } from "@/lib/runtime-config";
import type { ClientProfile } from "@/lib/types";
import { usePermissions } from "@/hooks/use-permissions";

export function useClientProfile() {
  const { data: session, status } = useSession();
  const { canManageData } = usePermissions();
  const email = session?.user?.email?.toLowerCase() ?? "";
  const [profile, setProfile] = useState<ClientProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (isAuthDisabledForLocal() || canManageData) {
      setProfile(null);
      setLoading(false);
      return;
    }
    if (!email) {
      setProfile(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<ClientProfile>(
        `v1/clients/profile?client_email_id=${encodeURIComponent(email)}`,
      );
      setProfile(data);
    } catch {
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }, [canManageData, email]);

  useEffect(() => {
    if (status === "loading") return;
    void refresh();
  }, [refresh, status]);

  return {
    email,
    profile,
    loading,
    error,
    refresh,
    needsOnboarding: !canManageData && !loading && !!email && !profile,
    clientEmailId: canManageData ? null : email || null,
    clientPhoneNumber: profile?.client_phone_number ?? null,
    collectionName: profile?.client_phone_number
      ? `phone_${profile.client_phone_number.replace(/\D/g, "")}`
      : null,
  };
}

export function clientScopeQuery(clientEmailId: string | null): string {
  if (!clientEmailId) return "";
  return `client_email_id=${encodeURIComponent(clientEmailId)}`;
}
