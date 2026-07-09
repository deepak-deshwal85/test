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

  const applyProfile = useCallback((data: ClientProfile) => {
    setProfile(data);
    setLoading(false);
  }, []);

  const refresh = useCallback(async () => {
    if (isAuthDisabledForLocal() || canManageData) {
      setProfile(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const path = email
        ? `v1/clients/profile?client_email_id=${encodeURIComponent(email)}`
        : "v1/clients/me";
      const data = await apiFetch<ClientProfile>(path);
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

  const clientEmailId = canManageData
    ? null
    : (profile?.client_email_id ?? email) || null;

  return {
    email: clientEmailId ?? email,
    profile,
    loading,
    refresh,
    applyProfile,
    needsOnboarding: !canManageData && !loading && !profile,
    clientEmailId,
    clientPhoneNumber: profile?.client_phone_number ?? null,
    collectionName: profile?.client_phone_number
      ? `phone_${profile.client_phone_number.replace(/\D/g, "")}`
      : null,
    ready: canManageData || loading || !!clientEmailId,
  };
}

export function clientScopeQuery(clientEmailId: string | null): string {
  if (!clientEmailId) return "";
  return `client_email_id=${encodeURIComponent(clientEmailId)}`;
}
