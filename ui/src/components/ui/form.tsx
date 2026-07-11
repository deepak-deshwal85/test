import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Label({
  children,
  htmlFor,
  className,
}: {
  children: ReactNode;
  htmlFor?: string;
  className?: string;
}) {
  return (
    <label
      htmlFor={htmlFor}
      className={cn(
        "mb-1.5 block text-sm font-medium text-foreground",
        className,
      )}
    >
      {children}
    </label>
  );
}

const fieldClassName =
  "w-full rounded-lg border border-input bg-card px-3 py-2.5 text-sm text-foreground shadow-sm transition-colors placeholder:text-muted-foreground hover:border-border focus:border-ring focus:outline-none focus:ring-2 focus:ring-ring/20 disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground";

export function Input({
  className,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(fieldClassName, className)} {...props} />;
}

export function Select({
  className,
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={cn(fieldClassName, className)} {...props}>
      {children}
    </select>
  );
}

export function Textarea({
  className,
  ...props
}: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(fieldClassName, "min-h-[100px] resize-y", className)}
      {...props}
    />
  );
}
