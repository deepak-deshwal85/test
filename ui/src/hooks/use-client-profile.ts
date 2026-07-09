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

  const refresh = useCallback(async () => {
    if (isAuthDisabledForLocal() || canManageData) {
      setProfile(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await apiFetch<ClientProfile>("v1/clients/me");
      setProfile(data);
    } catch {
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }, [canManageData]);

  useEffect(() => {
    if (status === "loading") return;
    void refresh();
  }, [refresh, status]);

  const clientEmailId = canManageData
    ? null
    : (profile?.client_email_id ?? email) || null;

  const businessPhone = profile?.client_business_phone_number ?? null;

  return {
    email: clientEmailId ?? email,
    profile,
    loading,
    refresh,
    clientEmailId,
    clientBusinessPhoneNumber: businessPhone,
    clientPersonalPhoneNumber: profile?.client_phone_number ?? null,
    collectionName: businessPhone
      ? `phone_${businessPhone.replace(/\D/g, "")}`
      : null,
    ready: canManageData || loading || !!clientEmailId,
  };
}

export function clientScopeQuery(clientEmailId: string | null): string {
  if (!clientEmailId) return "";
  return `client_email_id=${encodeURIComponent(clientEmailId)}`;
}
