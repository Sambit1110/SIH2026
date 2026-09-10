import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  try {
    const d = new Date(value);
    return d.toLocaleString(undefined, {
      year: "numeric", month: "short", day: "2-digit",
      hour: "2-digit", minute: "2-digit",
    });
  } catch {
    return value;
  }
}

export function timeAgo(value: string | null | undefined): string {
  if (!value) return "—";
  const then = new Date(value).getTime();
  const now = Date.now();
  const diffSec = Math.max(0, Math.floor((now - then) / 1000));
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO" | string;

export function severityColor(severity: Severity): string {
  switch (severity) {
    case "CRITICAL": return "var(--critical)";
    case "HIGH": return "var(--high)";
    case "MEDIUM": return "var(--medium)";
    case "LOW": return "var(--low)";
    default: return "var(--info)";
  }
}

export function severitySoft(severity: Severity): string {
  switch (severity) {
    case "CRITICAL": return "var(--critical-soft)";
    case "HIGH": return "var(--high-soft)";
    case "MEDIUM": return "var(--medium-soft)";
    case "LOW": return "var(--low-soft)";
    default: return "var(--info-soft)";
  }
}
