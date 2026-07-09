"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { usePathname } from "next/navigation";
import { useSession } from "next-auth/react";
import { apiFetch } from "@/lib/api-client";
import { isAuthDisabledForLocal } from "@/lib/runtime-config";
import type { ClientAdminListResponse, ClientProfile } from "@/lib/types";
import { usePermissions } from "@/hooks/use-permissions";

type ClientScopeContextValue = {
  selectedClient: ClientProfile | null;
  clients: ClientProfile[];
  loading: boolean;
  ready: boolean;
  error: string | null;
  clientEmailId: string | null;
  clientBusinessPhoneNumber: string | null;
  clientPersonalPhoneNumber: string | null;
  collectionName: string | null;
  refresh: () => Promise<void>;
  selectClient: (client: ClientProfile | null) => void;
  selectClientByEmail: (email: string) => void;
};

const STORAGE_KEY = "relaydesk_selected_client_email";

function readStoredEmail(): string | null {
  if (typeof window === "undefined") return null;
  const value = sessionStorage.getItem(STORAGE_KEY);
  return value?.trim().toLowerCase() || null;
}

function storeEmail(email: string | null) {
  if (typeof window === "undefined") return;
  if (email) sessionStorage.setItem(STORAGE_KEY, email);
  else sessionStorage.removeItem(STORAGE_KEY);
}

const ClientScopeContext = createContext<ClientScopeContextValue | null>(null);

export function ClientScopeProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { data: session, status } = useSession();
  const { canManageData } = usePermissions();
  const [clients, setClients] = useState<ClientProfile[]>([]);
  const [selectedClient, setSelectedClient] = useState<ClientProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestIdRef = useRef(0);

  const isPublicRoute =
    pathname === "/login" ||
    pathname.startsWith("/api/auth") ||
    pathname === "/pending-approval";

  const refresh = useCallback(async () => {
    if (isAuthDisabledForLocal() || isPublicRoute || status !== "authenticated") {
      setClients([]);
      setSelectedClient(null);
      setError(null);
      setLoading(false);
      return;
    }

    if (!isAuthDisabledForLocal() && !session?.accessToken) {
      setLoading(true);
      return;
    }

    const requestId = ++requestIdRef.current;
    setLoading(true);
    setError(null);
    try {
      if (canManageData) {
        const data = await apiFetch<ClientAdminListResponse>("v1/clients");
        if (requestId !== requestIdRef.current) return;
        setClients(data.clients);
        setSelectedClient((current) => {
          if (!data.clients.length) return null;
          const stored = readStoredEmail();
          if (stored) {
            const fromStorage = data.clients.find(
              (c) => c.client_email_id === stored,
            );
            if (fromStorage) return fromStorage;
          }
          if (current) {
            const match = data.clients.find(
              (c) => c.client_email_id === current.client_email_id,
            );
            if (match) return match;
          }
          return data.clients[0];
        });
      } else {
        const profile = await apiFetch<ClientProfile>("v1/clients/me");
        if (requestId !== requestIdRef.current) return;
        setClients([profile]);
        setSelectedClient(profile);
      }
    } catch (err) {
      if (requestId !== requestIdRef.current) return;
      setClients([]);
      setSelectedClient(null);
      setError(
        err instanceof Error ? err.message : "Failed to load client profile",
      );
    } finally {
      if (requestId === requestIdRef.current) {
        setLoading(false);
      }
    }
  }, [canManageData, isPublicRoute, session?.accessToken, status]);

  useEffect(() => {
    if (status === "loading") return;
    void refresh();
  }, [refresh, status]);

  const selectClient = useCallback((client: ClientProfile | null) => {
    setSelectedClient(client);
    storeEmail(client?.client_email_id ?? null);
  }, []);

  const selectClientByEmail = useCallback(
    (email: string) => {
      const normalized = email.trim().toLowerCase();
      const match = clients.find((c) => c.client_email_id === normalized);
      setSelectedClient(match ?? null);
      storeEmail(match?.client_email_id ?? null);
    },
    [clients],
  );

  const clientEmailId = selectedClient?.client_email_id ?? null;
  const businessPhone = selectedClient?.client_business_phone_number ?? null;

  const value = useMemo<ClientScopeContextValue>(
    () => ({
      selectedClient,
      clients,
      loading,
      ready: canManageData ? !loading : !loading && !!selectedClient,
      error,
      clientEmailId,
      clientBusinessPhoneNumber: businessPhone,
      clientPersonalPhoneNumber: selectedClient?.client_phone_number ?? null,
      collectionName: businessPhone
        ? `phone_${businessPhone.replace(/\D/g, "")}`
        : null,
      refresh,
      selectClient,
      selectClientByEmail,
    }),
    [
      selectedClient,
      clients,
      loading,
      error,
      canManageData,
      clientEmailId,
      businessPhone,
      refresh,
      selectClient,
      selectClientByEmail,
    ],
  );

  return (
    <ClientScopeContext.Provider value={value}>
      {children}
    </ClientScopeContext.Provider>
  );
}

export function useClientScope() {
  const context = useContext(ClientScopeContext);
  if (!context) {
    throw new Error("useClientScope must be used within ClientScopeProvider");
  }
  return context;
}

export function clientScopeQuery(clientEmailId: string | null): string {
  if (!clientEmailId) return "";
  return `client_email_id=${encodeURIComponent(clientEmailId)}`;
}
