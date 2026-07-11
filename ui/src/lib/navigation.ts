import type { LucideIcon } from "lucide-react";
import {
  BookOpen,
  Database,
  LayoutDashboard,
  Megaphone,
  Search,
  ShieldCheck,
  UserCircle,
  Users,
} from "lucide-react";
import type { RelayDeskRole } from "@/lib/roles";

export type NavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
};

export const APPROVED_CLIENT_NAV: NavItem[] = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/customers", label: "Customers", icon: Users },
  { href: "/campaigns", label: "Campaign", icon: Megaphone },
  { href: "/knowledge", label: "Knowledge", icon: BookOpen },
  { href: "/profile", label: "Profile", icon: UserCircle },
];

export const ADMIN_ONLY_NAV: NavItem[] = [
  { href: "/search", label: "Search", icon: Search },
  { href: "/collections", label: "Collections", icon: Database },
  { href: "/approve-clients", label: "Approve Clients", icon: ShieldCheck },
];

export const ADMIN_NAV: NavItem[] = [
  ...APPROVED_CLIENT_NAV.filter((item) => item.href !== "/profile"),
  ...ADMIN_ONLY_NAV,
  { href: "/profile", label: "Profile", icon: UserCircle },
];

/** Routes only admins may access (approved clients are redirected). */
export const ADMIN_ONLY_PATHS = [
  "/search",
  "/collections",
  "/approve-clients",
];

export function navForRole(role: RelayDeskRole | null | undefined): NavItem[] {
  if (role === "relaydesk-admins") {
    return ADMIN_NAV;
  }
  if (role === "approved-clients") {
    return APPROVED_CLIENT_NAV;
  }
  return [];
}

export function isAdminOnlyPath(pathname: string): boolean {
  return ADMIN_ONLY_PATHS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`),
  );
}
