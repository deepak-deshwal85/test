import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Card } from "./card";

export function StatCard({
  label,
  value,
  icon: Icon,
  badge,
  footer,
  className,
}: {
  label: string;
  value: ReactNode;
  icon?: LucideIcon;
  badge?: ReactNode;
  footer?: ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn("flex flex-col", className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-muted-foreground">{label}</p>
          <p className="mt-2 text-2xl font-semibold tracking-tight text-foreground">
            {value}
          </p>
        </div>
        {Icon ? (
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-50 text-brand-600 dark:bg-brand-50/10">
            <Icon className="h-5 w-5" aria-hidden />
          </div>
        ) : null}
        {badge}
      </div>
      {footer ? <div className="mt-4 pt-1">{footer}</div> : null}
    </Card>
  );
}
