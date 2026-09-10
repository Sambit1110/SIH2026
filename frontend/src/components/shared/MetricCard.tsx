import { cn } from "@/lib/utils";

export function MetricCard({
  label, value, hint, colorVar, icon: Icon,
}: {
  label: string;
  value: string | number;
  hint?: string;
  colorVar?: string;
  icon?: React.ComponentType<{ size?: number }>;
}) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--surface)] p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-[11px] uppercase tracking-wide text-[var(--text-faint)]">{label}</span>
        {Icon && (
          <span
            className="flex h-6 w-6 items-center justify-center rounded-md"
            style={{ background: colorVar ? `var(${colorVar}-soft)` : "var(--surface-active)", color: colorVar ? `var(${colorVar})` : "var(--text-muted)" }}
          >
            <Icon size={13} />
          </span>
        )}
      </div>
      <div className={cn("text-2xl font-semibold text-[var(--text)]")}>{value}</div>
      {hint && <span className="text-[11px] text-[var(--text-muted)]">{hint}</span>}
    </div>
  );
}
