"use client";

export {
  useClientScope,
  clientScopeQuery,
} from "@/contexts/client-scope-context";

import { useClientScope } from "@/contexts/client-scope-context";

/** @deprecated Use useClientScope — kept for compatibility */
export function useClientProfile() {
  const scope = useClientScope();
  return {
    email: scope.clientEmailId ?? "",
    profile: scope.selectedClient,
    loading: scope.loading,
    refresh: scope.refresh,
    clientEmailId: scope.clientEmailId,
    clientBusinessPhoneNumber: scope.clientBusinessPhoneNumber,
    clientPersonalPhoneNumber: scope.clientPersonalPhoneNumber,
    collectionName: scope.collectionName,
    ready: scope.ready,
  };
}
