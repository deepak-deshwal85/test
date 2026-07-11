import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Table({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("overflow-x-auto -mx-1", className)}>
      <table className="min-w-full text-left text-sm">{children}</table>
    </div>
  );
}

export function TableHead({ children }: { children: ReactNode }) {
  return (
    <thead>
      <tr className="border-b border-border text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {children}
      </tr>
    </thead>
  );
}

export function TableHeaderCell({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <th className={cn("px-3 py-3 font-medium", className)}>{children}</th>;
}

export function TableBody({ children }: { children: ReactNode }) {
  return <tbody className="divide-y divide-border">{children}</tbody>;
}

export function TableRow({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <tr className={cn("transition-colors hover:bg-muted/50", className)}>
      {children}
    </tr>
  );
}

export function TableCell({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <td className={cn("px-3 py-3.5 align-middle text-foreground/90", className)}>
      {children}
    </td>
  );
}
