"use client";

import { useSession } from "next-auth/react";
import {
  hasPermission,
  type Permission,
  type RelayDeskRole,
} from "@/lib/roles";

export function usePermissions() {
  const { data: session } = useSession();
  const role = (session?.user?.role ?? null) as RelayDeskRole | null;

  return {
    role,
    can: (permission: Permission) => hasPermission(role, permission),
    canUploadDocuments: hasPermission(role, "document_write"),
    canManageData: hasPermission(role, "admin"),
    isGuest: (role ?? "guest-clients") === "guest-clients",
    canManageOwnCustomers: hasPermission(role, "document_write"),
  };
}
