"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useClientProfile } from "@/hooks/use-client-profile";

const SKIP_PATHS = ["/login", "/signup", "/onboarding", "/api"];

export function ClientProfileGuard({ children }: { children: React.ReactNode }) {
  const { needsOnboarding, loading } = useClientProfile();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    const skip = SKIP_PATHS.some((path) => pathname.startsWith(path));
    if (!skip && needsOnboarding) {
      router.replace("/signup");
    }
  }, [loading, needsOnboarding, pathname, router]);

  return children;
}
