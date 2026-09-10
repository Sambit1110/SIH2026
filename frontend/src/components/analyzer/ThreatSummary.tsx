import { SeverityBadge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type { ThreatAnalysis } from "@/lib/api";
import { severityColor } from "@/lib/utils";

const SUB_SCORE_LABELS: Record<string, string> = {
  content: "Content Risk",
  sender: "Sender Risk",
  authentication: "Authentication Risk",
  url: "URL Risk",
  infrastructure: "Infrastructure Risk",
  impersonation: "Impersonation Risk",
};

export function ThreatSummary({ analysis }: { analysis: ThreatAnalysis }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
      <div className="lg:col-span-2 flex flex-col items-center justify-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] p-6">
        <div
          className="flex h-32 w-32 items-center justify-center rounded-full border-4"
          style={{ borderColor: severityColor(analysis.severity) }}
        >
          <div className="text-center">
            <div className="text-3xl font-bold text-[var(--text)]">{analysis.overall_score}</div>
            <div className="text-[10px] text-[var(--text-faint)] uppercase">/ 100</div>
          </div>
        </div>
        <SeverityBadge severity={analysis.severity} />
        <div className="text-center">
          <p className="text-sm font-medium text-[var(--text)]">{analysis.classification}</p>
          <p className="text-xs text-[var(--text-muted)] mt-0.5">{analysis.confidence}% confidence</p>
        </div>
      </div>

      <div className="lg:col-span-3 flex flex-col gap-3 justify-center">
        {Object.entries(analysis.sub_scores).map(([key, value]) => (
          <div key={key}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-[var(--text-muted)]">{SUB_SCORE_LABELS[key] ?? key}</span>
              <span className="text-[var(--text)] font-medium mono">{value}</span>
            </div>
            <Progress value={value} colorVar={value >= 65 ? "--critical" : value >= 35 ? "--high" : "--low"} />
          </div>
        ))}
      </div>
    </div>
  );
}

export function ExplanationFactors({ factors }: { factors: ThreatAnalysis["factors"] }) {
  if (factors.length === 0) {
    return <p className="text-sm text-[var(--text-muted)]">No contributing risk factors were identified.</p>;
  }
  return (
    <div className="flex flex-col divide-y divide-[var(--border)]">
      {factors.map((f, i) => (
        <div key={i} className="flex items-start gap-3 py-2.5">
          <span
            className="mono text-xs font-semibold rounded px-1.5 py-0.5 shrink-0 mt-0.5"
            style={{
              color: f.points >= 20 ? "var(--critical)" : f.points >= 10 ? "var(--high)" : "var(--medium)",
              background: f.points >= 20 ? "var(--critical-soft)" : f.points >= 10 ? "var(--high-soft)" : "var(--medium-soft)",
            }}
          >
            +{f.points}
          </span>
          <div className="min-w-0">
            <p className="text-sm text-[var(--text)]">{f.label}</p>
            <p className="text-xs text-[var(--text-muted)] mt-0.5">{f.reason}</p>
          </div>
          <span className="ml-auto shrink-0 text-[10px] uppercase tracking-wide text-[var(--text-faint)]">{f.category}</span>
        </div>
      ))}
    </div>
  );
}
