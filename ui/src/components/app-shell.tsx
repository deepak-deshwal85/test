"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut, Radio } from "lucide-react";
import { signOut, useSession } from "next-auth/react";
import { ClientHeaderBar } from "@/components/client-header-bar";
import { GuestOnboardingGate } from "@/components/guest-onboarding-gate";
import { ThemeToggle } from "@/components/theme-toggle";
import { usePermissions } from "@/hooks/use-permissions";
import { navForRole } from "@/lib/navigation";
import { roleLabel } from "@/lib/roles";
import type { RelayDeskRole } from "@/lib/roles";
import { cn } from "@/lib/utils";

function SidebarNav({
  items,
  pathname,
  onNavigate,
}: {
  items: ReturnType<typeof navForRole>;
  pathname: string;
  onNavigate?: () => void;
}) {
  return (
    <nav className="flex flex-1 flex-col gap-0.5" aria-label="Main navigation">
      {items.map((item) => {
        const active =
          item.href === "/"
            ? pathname === "/"
            : pathname.startsWith(item.href);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40",
              active
                ? "bg-primary text-primary-foreground shadow-sm"
                : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
            )}
          >
            <Icon className="h-4 w-4 shrink-0" aria-hidden />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { data: session } = useSession();
  const { isGuest, role } = usePermissions();
  const sidebarNav = navForRole(role);
  const userRole = (role ?? "guest-clients") as RelayDeskRole;

  if (isGuest) {
    return (
      <div className="min-h-dvh bg-background">
        <header className="border-b border-border bg-card px-4 py-3 sm:px-6">
          <div className="mx-auto flex max-w-5xl items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Radio className="h-5 w-5 text-brand-600" aria-hidden />
              <span className="text-sm font-semibold text-foreground">RelayDesk</span>
            </div>
            <ThemeToggle compact />
          </div>
        </header>
        <GuestOnboardingGate />
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-background lg:grid lg:grid-cols-[272px_1fr]">
      <aside className="hidden border-r border-border bg-card lg:flex lg:flex-col">
        <div className="flex h-16 items-center gap-2.5 border-b border-border px-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
            <Radio className="h-4 w-4" aria-hidden />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-foreground">RelayDesk</p>
            <p className="truncate text-xs text-muted-foreground">Operations console</p>
          </div>
        </div>

        <div className="flex flex-1 flex-col p-4">
          <SidebarNav items={sidebarNav} pathname={pathname} />
        </div>

        <div className="border-t border-border p-4">
          <div className="mb-3 rounded-lg bg-muted px-3 py-2.5">
            <p className="truncate text-sm font-medium text-foreground">
              {session?.user?.name ?? session?.user?.email ?? "Signed in"}
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">{roleLabel(userRole)}</p>
          </div>
          <div className="mb-2 flex items-center gap-2">
            <ThemeToggle compact />
            <span className="text-xs text-muted-foreground">Appearance</span>
          </div>
          <button
            type="button"
            onClick={() => signOut({ callbackUrl: "/login" })}
            className={cn(
              "flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground",
              "transition-colors hover:bg-accent hover:text-accent-foreground",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40",
            )}
          >
            <LogOut className="h-4 w-4" aria-hidden />
            Sign out
          </button>
        </div>
      </aside>

      <div className="flex min-h-dvh min-w-0 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-card/95 px-4 backdrop-blur-sm lg:hidden">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Radio className="h-3.5 w-3.5" aria-hidden />
            </div>
            <span className="text-sm font-semibold text-foreground">RelayDesk</span>
          </div>
          <ThemeToggle compact />
        </header>

        <ClientHeaderBar />

        <main className="flex-1 px-4 py-6 pb-24 sm:px-6 lg:px-8 lg:py-8 lg:pb-8">
          <div className="mx-auto max-w-6xl">{children}</div>
        </main>

        <nav
          className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card/95 backdrop-blur-sm lg:hidden"
          aria-label="Mobile navigation"
        >
          <div className="flex overflow-x-auto px-2 py-2 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {sidebarNav.map((item) => {
              const active =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href);
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex min-w-[4.5rem] flex-1 flex-col items-center gap-1 rounded-lg px-2 py-1.5 text-[10px] font-medium",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40",
                    active ? "text-primary" : "text-muted-foreground",
                  )}
                >
                  <Icon className="h-5 w-5" aria-hidden />
                  <span className="max-w-full truncate">{item.label}</span>
                </Link>
              );
            })}
          </div>
        </nav>
      </div>
    </div>
  );
}
