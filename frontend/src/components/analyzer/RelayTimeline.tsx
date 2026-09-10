import type { RelayHop } from "@/lib/api";
import { EmptyState } from "@/components/shared/States";
import { AlertTriangle, CheckCircle2 } from "lucide-react";

export function RelayTimeline({ hops }: { hops: RelayHop[] }) {
  if (hops.length === 0) return <EmptyState title="No relay chain found" description="No Received headers were present in this message." />;

  return (
    <div className="relative pl-6">
      <div className="absolute left-[9px] top-2 bottom-2 w-px bg-[var(--border-strong)]" />
      <div className="flex flex-col gap-5">
        {hops.map((hop) => {
          const hasFlags = hop.flags.length > 0;
          return (
            <div key={hop.sequence} className="relative">
              <div
                className="absolute -left-6 top-0.5 flex h-4.5 w-4.5 items-center justify-center rounded-full"
                style={{ background: hasFlags ? "var(--high-soft)" : "var(--low-soft)" }}
              >
                {hasFlags ? <AlertTriangle size={11} color="var(--high)" /> : <CheckCircle2 size={11} color="var(--low)" />}
              </div>
              <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] p-3.5">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] uppercase tracking-wide text-[var(--text-faint)]">Hop {hop.sequence}</span>
                    {hop.is_earliest_reliable && (
                      <span className="text-[10px] rounded-full bg-[var(--accent-soft)] text-[var(--accent)] px-2 py-0.5">
                        Earliest reliable observed node
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-[var(--text-muted)]">{hop.timestamp ?? "no timestamp"}</span>
                </div>
                <p className="mono text-sm text-[var(--text)] mt-1.5">{hop.hostname}{hop.ip && ` [${hop.ip}]`}</p>
                {hop.geo && (
                  <p className="text-xs text-[var(--text-muted)] mt-1">
                    {hop.geo.city}, {hop.geo.country} · {hop.geo.isp} · {hop.geo.asn}
                    <span className="ml-2 text-[var(--text-faint)]">({hop.geo.source})</span>
                  </p>
                )}
                {hop.flags.length > 0 && (
                  <div className="flex gap-1.5 flex-wrap mt-2">
                    {hop.flags.map((f) => (
                      <span key={f} className="text-[10px] rounded-full bg-[var(--high-soft)] text-[var(--high)] px-2 py-0.5">
                        {f.replace(/_/g, " ")}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
