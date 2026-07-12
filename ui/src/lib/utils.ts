import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

export function statusColor(status: string): string {
  switch (status) {
    case "completed":
      return "bg-emerald-100 text-emerald-800";
    case "running":
      return "bg-blue-100 text-blue-800";
    case "failed":
      return "bg-red-100 text-red-800";
    case "pending":
      return "bg-amber-100 text-amber-800";
    default:
      return "bg-slate-100 text-slate-700";
  }
}

export function consumerStatusLabel(value: string): string {
  switch (value) {
    case "READY":
      return "Ready";
    case "MEETING_SCHEDULED":
      return "Meeting scheduled";
    case "MEETING_NOT_SCHEDULED":
      return "No meeting";
    default:
      return value;
  }
}

export function consumerStatusColor(value: string): string {
  switch (value) {
    case "READY":
      return "bg-emerald-50 text-emerald-700";
    case "MEETING_SCHEDULED":
      return "bg-blue-50 text-blue-700";
    case "MEETING_NOT_SCHEDULED":
      return "bg-zinc-100 text-zinc-600";
    default:
      return "bg-zinc-100 text-zinc-600";
  }
}

export function callScheduleLabel(value: string): string {
  return value === "yes" ? "Yes" : "No";
}
