import * as React from "react";
import { cn } from "@/lib/utils";

export function Badge({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { variant?: "default" | "outline" | "soft" }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium leading-none",
        variant === "default" && "bg-[var(--surface-active)] text-[var(--text)]",
        variant === "outline" && "border border-[var(--border-strong)] text-[var(--text-muted)]",
        variant === "soft" && "bg-[var(--accent-soft)] text-[var(--accent)]",
        className,
      )}
      {...props}
    />
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, { bg: string; fg: string; label: string }> = {
    CRITICAL: { bg: "var(--critical-soft)", fg: "var(--critical)", label: "Critical" },
    HIGH: { bg: "var(--high-soft)", fg: "var(--high)", label: "High" },
    MEDIUM: { bg: "var(--medium-soft)", fg: "var(--medium)", label: "Medium" },
    LOW: { bg: "var(--low-soft)", fg: "var(--low)", label: "Low" },
  };
  const s = map[severity] ?? { bg: "var(--info-soft)", fg: "var(--info)", label: severity };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
        severity === "CRITICAL" && "pulse-critical",
      )}
      style={{ background: s.bg, color: s.fg }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: s.fg }} />
      {s.label}
    </span>
  );
}

export function RiskBadge({ risk }: { risk: string }) {
  return <SeverityBadge severity={risk} />;
}
