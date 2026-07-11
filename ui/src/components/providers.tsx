"use client";

import { SessionProvider } from "next-auth/react";
import { ThemeProvider } from "@/components/theme-provider";
import { ClientScopeProvider } from "@/contexts/client-scope-context";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <SessionProvider>
        <ClientScopeProvider>{children}</ClientScopeProvider>
      </SessionProvider>
    </ThemeProvider>
  );
}
