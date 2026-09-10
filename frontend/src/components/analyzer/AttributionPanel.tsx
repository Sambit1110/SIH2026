import type { ThreatAnalysis } from "@/lib/api";
import { ShieldAlert, Info } from "lucide-react";

export function AttributionPanel({ analysis }: { analysis: ThreatAnalysis }) {
  const { attribution, lookalike_findings } = analysis;
  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] p-4">
        <div className="flex items-center gap-2 mb-2">
          <ShieldAlert size={16} className="text-[var(--accent)]" />
          <span className="text-sm font-semibold text-[var(--text)]">{attribution.conclusion}</span>
        </div>
        <p className="text-xs text-[var(--text-muted)] mb-3">
          Evidence strength: <span className="text-[var(--text)] font-medium">{attribution.evidence_strength}</span>
        </p>
        <ul className="flex flex-col gap-1.5">
          {attribution.supporting_indicators.map((s, i) => (
            <li key={i} className="text-sm text-[var(--text)] flex gap-2">
              <span className="text-[var(--accent)] mt-1">•</span> {s}
            </li>
          ))}
        </ul>
      </div>

      {lookalike_findings.length > 0 && (
        <div>
          <p className="text-xs uppercase tracking-wide text-[var(--text-faint)] mb-2">Lookalike Domain Analysis</p>
          <div className="flex flex-col gap-2">
            {lookalike_findings.map((f, i) => (
              <div key={i} className="rounded-md border border-[var(--border)] bg-[var(--bg-elevated)] p-3 text-sm">
                <div className="flex justify-between">
                  <span className="mono text-[var(--text)]">{f.observed_domain}</span>
                  <span className="text-[var(--critical)] text-xs font-medium">{f.confidence} · {f.similarity}%</span>
                </div>
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  Resembles <span className="text-[var(--text)]">{f.target_brand}</span> — {f.reason}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex gap-2 rounded-lg bg-[var(--info-soft)] border border-[var(--border)] p-3">
        <Info size={15} className="text-[var(--info)] shrink-0 mt-0.5" />
        <p className="text-xs text-[var(--text-muted)] leading-relaxed">{attribution.limitations}</p>
      </div>
    </div>
  );
}

export function recommendedActions(analysis: ThreatAnalysis): string[] {
  const actions: string[] = [];
  if (analysis.severity === "CRITICAL" || analysis.severity === "HIGH") {
    actions.push("Quarantine or block further delivery from the observed sender domain and IP infrastructure pending review.");
    actions.push("Notify the targeted recipient(s) and any impersonated party (e.g. the executive or vendor referenced).");
    actions.push("Do not action any payment, credential, or account-change request contained in this message.");
  }
  if (analysis.sub_scores.authentication >= 20) {
    actions.push("Review and tighten SPF/DKIM/DMARC enforcement policy for the organization's own domain(s).");
  }
  if (analysis.sub_scores.impersonation >= 20) {
    actions.push("Consider defensive domain registration or monitoring for close lookalikes of the impersonated brand.");
  }
  if (analysis.severity === "LOW") {
    actions.push("No immediate action required; retain for baseline reference.");
  }
  actions.push("Preserve original evidence and chain-of-custody records for potential escalation.");
  return actions;
}

export function RecommendedActions({ analysis }: { analysis: ThreatAnalysis }) {
  return (
    <ul className="flex flex-col gap-2">
      {recommendedActions(analysis).map((a, i) => (
        <li key={i} className="flex gap-2 text-sm text-[var(--text)]">
          <span className="text-[var(--low)] mt-0.5">✓</span> {a}
        </li>
      ))}
    </ul>
  );
}
