import type { HeaderFinding } from "@/lib/api";
import { severityColor, severitySoft } from "@/lib/utils";

export function HeaderForensicsPanel({ findings, rawHeaders }: {
  findings: HeaderFinding[];
  rawHeaders: Array<{ name: string; value: string }>;
}) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
      <div>
        <p className="text-xs uppercase tracking-wide text-[var(--text-faint)] mb-2">Forensic Findings</p>
        <div className="flex flex-col gap-2">
          {findings.map((f, i) => (
            <div
              key={i}
              className="rounded-md border-l-2 px-3 py-2"
              style={{ borderColor: severityColor(f.severity), background: severitySoft(f.severity) }}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-[var(--text)]">{f.issue}</span>
                <span className="text-[10px] uppercase tracking-wide" style={{ color: severityColor(f.severity) }}>
                  {f.severity}
                </span>
              </div>
              <p className="text-xs text-[var(--text-muted)] mt-1">{f.detail}</p>
            </div>
          ))}
        </div>
      </div>
      <div>
        <p className="text-xs uppercase tracking-wide text-[var(--text-faint)] mb-2">Raw Headers</p>
        <div className="max-h-[420px] overflow-y-auto scrollbar-thin rounded-md border border-[var(--border)] bg-[var(--bg-elevated)]">
          {rawHeaders.map((h, i) => (
            <div key={i} className="px-3 py-1.5 border-b border-[var(--border)] last:border-0 text-xs">
              <span className="text-[var(--accent)] mono">{h.name}:</span>{" "}
              <span className="text-[var(--text-muted)] mono break-all">{h.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
