"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  Database,
  LayoutDashboard,
  LogOut,
  PhoneCall,
  Search,
  UserCircle,
  Users,
} from "lucide-react";
import { signOut } from "next-auth/react";
import { ClientHeaderBar } from "@/components/client-header-bar";
import { GuestOnboardingGate } from "@/components/guest-onboarding-gate";
import { usePermissions } from "@/hooks/use-permissions";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/customers", label: "Customers", icon: Users },
  { href: "/call-jobs", label: "Call Jobs", icon: PhoneCall },
  { href: "/knowledge", label: "Knowledge", icon: BookOpen },
  { href: "/search", label: "Search", icon: Search },
  { href: "/collections", label: "Collections", icon: Database },
];

const clientNav = [
  { href: "/profile", label: "Profile", icon: UserCircle },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { isGuest, canManageData } = usePermissions();
  const sidebarNav = canManageData ? nav : [...nav, ...clientNav];

  if (isGuest) {
    return (
      <div className="min-h-dvh bg-slate-50">
        <header className="border-b border-slate-200/80 bg-white/80 px-4 py-3 backdrop-blur">
          <p className="text-sm font-semibold text-slate-900">RelayDesk</p>
        </header>
        <GuestOnboardingGate />
      </div>
    );
  }

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[260px_1fr]">
        <aside className="hidden border-r border-slate-200/80 bg-white/70 p-5 backdrop-blur lg:flex lg:flex-col">
          <div className="mb-8">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-600">
              RelayDesk
            </p>
            <h2 className="mt-1 text-lg font-semibold text-slate-900">
              Operations Console
            </h2>
          </div>
          <nav className="flex flex-1 flex-col gap-1">
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
                  className={cn(
                    "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition",
                    active
                      ? "bg-brand-600 text-white shadow-sm"
                      : "text-slate-600 hover:bg-slate-100",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <button
            type="button"
            onClick={() => signOut({ callbackUrl: "/login" })}
            className="mt-4 flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm text-slate-600 hover:bg-slate-100"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </aside>

        <div className="flex min-h-dvh flex-col">
          <header className="sticky top-0 z-10 border-b border-slate-200/80 bg-white/80 px-4 py-3 backdrop-blur lg:hidden">
            <p className="text-sm font-semibold text-slate-900">RelayDesk</p>
          </header>

          <ClientHeaderBar />

          <main className="flex-1 px-4 py-6 pb-24 lg:px-8 lg:py-8">{children}</main>

          <nav
            className={cn(
              "fixed inset-x-0 bottom-0 z-20 grid border-t border-slate-200 bg-white/95 px-1 py-2 backdrop-blur lg:hidden",
              canManageData ? "grid-cols-6" : "grid-cols-7",
            )}
          >
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
                  className={cn(
                    "flex flex-col items-center gap-1 rounded-lg px-1 py-1 text-[10px] font-medium",
                    active ? "text-brand-600" : "text-slate-500",
                  )}
                >
                  <Icon className="h-4 w-4" />
                  <span className="truncate">{item.label.split(" ")[0]}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
  );
}
