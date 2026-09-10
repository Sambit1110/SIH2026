import type { AuthResult } from "@/lib/api";
import { ShieldCheck, ShieldX, ShieldQuestion } from "lucide-react";

function ResultPill({ label, value }: { label: string; value: string }) {
  const isPass = value === "PASS";
  const isFail = value === "FAIL";
  const Icon = isPass ? ShieldCheck : isFail ? ShieldX : ShieldQuestion;
  const color = isPass ? "var(--low)" : isFail ? "var(--critical)" : "var(--text-muted)";
  const bg = isPass ? "var(--low-soft)" : isFail ? "var(--critical-soft)" : "var(--surface-active)";

  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border border-[var(--border)] p-4 flex-1" style={{ background: bg }}>
      <Icon size={22} color={color} />
      <span className="text-xs uppercase tracking-wide text-[var(--text-muted)]">{label}</span>
      <span className="text-sm font-semibold" style={{ color }}>{value}</span>
    </div>
  );
}

export function AuthPanel({ auth }: { auth: AuthResult }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-3">
        <ResultPill label="SPF" value={auth.spf} />
        <ResultPill label="DKIM" value={auth.dkim} />
        <ResultPill label="DMARC" value={auth.dmarc} />
      </div>
      <div className="rounded-md bg-[var(--bg-elevated)] border border-[var(--border)] px-3 py-2 text-xs text-[var(--text-muted)]">
        <span className="text-[var(--text-faint)] uppercase tracking-wide text-[10px] mr-2">Source</span>
        {auth.source}
      </div>
      {auth.raw_auth_header && (
        <div className="rounded-md bg-[var(--bg-elevated)] border border-[var(--border)] px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-[var(--text-faint)] mb-1">Raw Authentication-Results header</p>
          <p className="mono text-xs text-[var(--text-muted)] break-all">{auth.raw_auth_header}</p>
        </div>
      )}
    </div>
  );
}
