import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Card({
  className,
  children,
  padding = true,
}: {
  className?: string;
  children: ReactNode;
  padding?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-card text-card-foreground shadow-[var(--shadow-card)]",
        padding && "p-5 sm:p-6",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={cn("mb-4 flex flex-col gap-1", className)}>{children}</div>
  );
}

export function CardTitle({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <h2
      className={cn(
        "text-base font-semibold tracking-tight text-card-foreground",
        className,
      )}
    >
      {children}
    </h2>
  );
}

export function CardDescription({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <p className={cn("text-sm text-muted-foreground", className)}>{children}</p>
  );
}
