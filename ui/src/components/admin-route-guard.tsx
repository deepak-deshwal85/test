"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { isAdminOnlyPath } from "@/lib/navigation";
import { usePermissions } from "@/hooks/use-permissions";

/** Redirect approved clients away from admin-only routes. */
export function AdminRouteGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { canManageData, isGuest } = usePermissions();

  useEffect(() => {
    if (isGuest) return;
    if (!canManageData && isAdminOnlyPath(pathname)) {
      router.replace("/");
    }
  }, [canManageData, isGuest, pathname, router]);

  if (!canManageData && isAdminOnlyPath(pathname)) {
    return null;
  }

  return <>{children}</>;
}
