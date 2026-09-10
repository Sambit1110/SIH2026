import { cn } from "@/lib/utils";

export function Progress({
  value, className, colorVar = "--accent",
}: { value: number; className?: string; colorVar?: string }) {
  return (
    <div className={cn("h-1.5 w-full overflow-hidden rounded-full bg-[var(--surface-active)]", className)}>
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{ width: `${Math.min(100, Math.max(0, value))}%`, background: `var(${colorVar})` }}
      />
    </div>
  );
}
