"use client";

import { useQuery } from "@tanstack/react-query";
import { Printer } from "lucide-react";
import { api } from "@/lib/api";
import { LoadingState, ErrorState } from "@/components/shared/States";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/utils";

interface ReportFactor { label: string; points: number; category: string; reason: string }
interface ReportHeaderFinding { issue: string; severity: string; detail: string }
interface ReportIoc { type: string; value: string; risk: string; confidence: number; source: string }
interface ReportDomainIntel { domain: string; registrar: string; created_date: string; reputation: string; source: string }
interface ReportIpIntel { ip: string; country: string; city: string; isp: string; asn: string; reputation: string; source: string }
interface ReportRelayHop { sequence: number; hostname: string; ip: string | null; timestamp: string | null; is_earliest_reliable: boolean }
interface ReportGeo { ip: string; city: string; country: string; lat: number; lon: number; source: string }
interface ReportTimelineEvent { occurred_at: string; description: string }

interface ReportData {
  case_information?: { title: string; case_number: string; status: string; analyst: string; created_at: string; severity: string };
  executive_summary?: string;
  email_metadata?: { from: string; to: string; subject: string; date: string; message_id: string };
  threat_classification?: { classification: string; confidence: number };
  risk_score?: { overall_score: number; severity: string; sub_scores: Record<string, number>; factors: ReportFactor[] };
  authentication_analysis?: { spf: string; dkim: string; dmarc: string; source: string } | null;
  header_analysis?: ReportHeaderFinding[];
  ioc_findings?: ReportIoc[];
  url_analysis?: string[];
  domain_intelligence?: ReportDomainIntel[];
  ip_intelligence?: ReportIpIntel[];
  relay_trace?: ReportRelayHop[];
  geolocation?: ReportGeo[];
  infrastructure_relationships?: string;
  timeline?: ReportTimelineEvent[];
  evidence_integrity?: { filename: string; sha256: string; acquisition_method: string; integrity_status: string } | null;
  attribution_assessment?: { conclusion: string; supporting_indicators: string[]; limitations: string } | null;
  confidence_levels?: { classification_confidence: number; attribution_evidence_strength: string };
  recommended_actions?: string[];
}

export function ReportView({ reportId }: { reportId: string }) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["report", reportId],
    queryFn: () => api.getReport(reportId),
  });

  if (isLoading) return <LoadingState label="Loading report..." />;
  if (isError || !data) return <ErrorState onRetry={refetch} />;

  const r = data.data as ReportData;

  return (
    <div className="flex flex-col gap-4">
      <div className="no-print flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-[var(--text)]">Forensic Report</h2>
          <p className="text-sm text-[var(--text-muted)]">Generated {formatDate(data.generated_at)}</p>
        </div>
        <Button onClick={() => window.print()}><Printer size={14} /> Print / Save as PDF</Button>
      </div>

      <div className="mx-auto w-full max-w-[820px] rounded-lg bg-white text-slate-900 shadow-2xl print:shadow-none">
        <div className="p-10 flex flex-col gap-8">
          <header className="flex items-start justify-between border-b border-slate-200 pb-6">
            <div>
              <p className="text-xs uppercase tracking-widest text-slate-400 font-semibold">Trace-X Forensic Intelligence Report</p>
              <h1 className="text-2xl font-bold mt-1">{r.case_information?.title}</h1>
              <p className="text-sm text-slate-500 mt-1">Case {r.case_information?.case_number}</p>
            </div>
            <div className="text-right text-xs text-slate-500">
              <p>Generated {formatDate(data.generated_at)}</p>
              <p className="mt-1 font-semibold text-slate-700">{r.case_information?.severity} SEVERITY</p>
            </div>
          </header>

          <Section n={1} title="Case Information">
            <KV label="Status" value={r.case_information?.status} />
            <KV label="Analyst" value={r.case_information?.analyst} />
            <KV label="Opened" value={formatDate(r.case_information?.created_at)} />
          </Section>

          <Section n={2} title="Executive Summary">
            <p className="text-sm leading-relaxed">{r.executive_summary}</p>
          </Section>

          <Section n={3} title="Email Metadata">
            <KV label="From" value={r.email_metadata?.from} mono />
            <KV label="To" value={r.email_metadata?.to} mono />
            <KV label="Subject" value={r.email_metadata?.subject} />
            <KV label="Date" value={r.email_metadata?.date} />
            <KV label="Message-ID" value={r.email_metadata?.message_id} mono />
          </Section>

          <Section n={4} title="Threat Classification">
            <KV label="Classification" value={r.threat_classification?.classification} />
            <KV label="Confidence" value={`${r.threat_classification?.confidence}%`} />
          </Section>

          <Section n={5} title="Risk Score">
            <p className="text-3xl font-bold mb-2">{r.risk_score?.overall_score}/100 — {r.risk_score?.severity}</p>
            <div className="grid grid-cols-3 gap-3 mb-3">
              {r.risk_score?.sub_scores && Object.entries(r.risk_score.sub_scores).map(([k, v]) => (
                <div key={k} className="rounded border border-slate-200 p-2 text-center">
                  <div className="text-lg font-semibold">{String(v)}</div>
                  <div className="text-[10px] uppercase text-slate-500">{k}</div>
                </div>
              ))}
            </div>
            <div className="flex flex-col gap-1">
              {(r.risk_score?.factors ?? []).slice(0, 12).map((f: ReportFactor, i: number) => (
                <p key={i} className="text-xs">
                  <span className="font-semibold text-red-600">+{f.points}</span> {f.label} — <span className="text-slate-500">{f.reason}</span>
                </p>
              ))}
            </div>
          </Section>

          <Section n={6} title="Authentication Analysis">
            {r.authentication_analysis ? (
              <>
                <KV label="SPF" value={r.authentication_analysis.spf} />
                <KV label="DKIM" value={r.authentication_analysis.dkim} />
                <KV label="DMARC" value={r.authentication_analysis.dmarc} />
                <KV label="Source" value={r.authentication_analysis.source} />
              </>
            ) : <Empty />}
          </Section>

          <Section n={7} title="Header Analysis">
            {(r.header_analysis ?? []).map((f: ReportHeaderFinding, i: number) => (
              <p key={i} className="text-xs mb-1"><span className="font-semibold">{f.issue}</span> ({f.severity}) — {f.detail}</p>
            ))}
          </Section>

          <Section n={8} title="IOC Findings">
            <p className="text-xs text-slate-500 mb-2">{(r.ioc_findings ?? []).length} indicator(s) extracted.</p>
            <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
              {(r.ioc_findings ?? []).slice(0, 20).map((i: ReportIoc, idx: number) => (
                <p key={idx} className="mono truncate">{i.type}: {i.value} <span className="text-slate-400">({i.risk})</span></p>
              ))}
            </div>
          </Section>

          <Section n={9} title="URL Analysis">
            {(r.url_analysis ?? []).length === 0 ? <Empty /> : (r.url_analysis ?? []).map((u: string, i: number) => (
              <p key={i} className="text-xs mono break-all">{u}</p>
            ))}
          </Section>

          <Section n={10} title="Domain Intelligence">
            {(r.domain_intelligence ?? []).map((d: ReportDomainIntel, i: number) => (
              <div key={i} className="mb-2 text-xs">
                <p className="font-semibold">{d.domain} — {d.reputation}</p>
                <p className="text-slate-500">Registrar: {d.registrar} · Created: {d.created_date} · Source: {d.source}</p>
              </div>
            ))}
          </Section>

          <Section n={11} title="IP Intelligence">
            {(r.ip_intelligence ?? []).map((ip: ReportIpIntel, i: number) => (
              <div key={i} className="mb-2 text-xs">
                <p className="font-semibold">{ip.ip} — {ip.reputation}</p>
                <p className="text-slate-500">{ip.city}, {ip.country} · {ip.isp} · {ip.asn} · Source: {ip.source}</p>
              </div>
            ))}
          </Section>

          <Section n={12} title="Relay Trace">
            {(r.relay_trace ?? []).map((h: ReportRelayHop, i: number) => (
              <p key={i} className="text-xs mono mb-1">
                Hop {h.sequence}: {h.hostname} [{h.ip ?? "no IP"}] — {h.timestamp ?? "no timestamp"}
                {h.is_earliest_reliable && <span className="text-blue-600 font-semibold"> (earliest reliable)</span>}
              </p>
            ))}
          </Section>

          <Section n={13} title="Geolocation">
            {(r.geolocation ?? []).length === 0 ? <Empty /> : (r.geolocation ?? []).map((g: ReportGeo, i: number) => (
              <p key={i} className="text-xs">{g.ip}: {g.city}, {g.country} ({g.lat}, {g.lon}) — {g.source}</p>
            ))}
            <p className="text-[11px] text-slate-400 mt-2 italic">
              Geolocation reflects observed infrastructure location only, not physical attacker identity or location.
            </p>
          </Section>

          <Section n={14} title="Infrastructure Relationships">
            <p className="text-xs text-slate-500">{r.infrastructure_relationships}</p>
          </Section>

          <Section n={15} title="Timeline">
            {(r.timeline ?? []).map((t: ReportTimelineEvent, i: number) => (
              <p key={i} className="text-xs mb-1">{formatDate(t.occurred_at)} — {t.description}</p>
            ))}
          </Section>

          <Section n={16} title="Evidence Integrity">
            {r.evidence_integrity ? (
              <>
                <KV label="Filename" value={r.evidence_integrity.filename} />
                <KV label="SHA-256" value={r.evidence_integrity.sha256} mono />
                <KV label="Acquisition" value={r.evidence_integrity.acquisition_method} />
                <KV label="Integrity" value={r.evidence_integrity.integrity_status} />
              </>
            ) : <Empty />}
          </Section>

          <Section n={17} title="Attribution Assessment">
            {r.attribution_assessment ? (
              <>
                <p className="text-sm font-semibold mb-1">{r.attribution_assessment.conclusion}</p>
                <ul className="list-disc pl-5 text-xs mb-2">
                  {(r.attribution_assessment.supporting_indicators ?? []).map((s: string, i: number) => <li key={i}>{s}</li>)}
                </ul>
                <p className="text-[11px] text-slate-400 italic">{r.attribution_assessment.limitations}</p>
              </>
            ) : <Empty />}
          </Section>

          <Section n={18} title="Confidence Levels">
            <KV label="Classification Confidence" value={`${r.confidence_levels?.classification_confidence}%`} />
            <KV label="Attribution Evidence Strength" value={r.confidence_levels?.attribution_evidence_strength} />
          </Section>

          <Section n={19} title="Recommended Actions">
            <ul className="list-disc pl-5 text-sm flex flex-col gap-1">
              {(r.recommended_actions ?? []).map((a: string, i: number) => <li key={i}>{a}</li>)}
            </ul>
          </Section>

          <footer className="border-t border-slate-200 pt-4 text-[10px] text-slate-400">
            Generated by Trace-X — AI-Powered Email Threat Detection, Geolocation and Forensic Intelligence Platform.
            This report is an investigative aid; conclusions herein are not a substitute for legal or judicial determination.
          </footer>
        </div>
      </div>
    </div>
  );
}

function Section({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <section className="break-inside-avoid">
      <h2 className="text-sm font-bold uppercase tracking-wide text-slate-400 mb-2">{n}. {title}</h2>
      <div className="flex flex-col gap-1">{children}</div>
    </section>
  );
}

function KV({ label, value, mono }: { label: string; value?: string | number | null; mono?: boolean }) {
  return (
    <div className="flex justify-between gap-4 text-sm">
      <span className="text-slate-500">{label}</span>
      <span className={`text-right break-all ${mono ? "mono text-xs" : ""}`}>{value ?? "—"}</span>
    </div>
  );
}

function Empty() {
  return <p className="text-xs text-slate-400 italic">Not applicable.</p>;
}
