"use client";

import { SessionProvider } from "next-auth/react";
import { ClientScopeProvider } from "@/contexts/client-scope-context";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <ClientScopeProvider>{children}</ClientScopeProvider>
    </SessionProvider>
  );
}
