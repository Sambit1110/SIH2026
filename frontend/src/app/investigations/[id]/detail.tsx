"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, ShieldCheck, Mail as MailIcon, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";
import { LoadingState, ErrorState, EmptyState } from "@/components/shared/States";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SeverityBadge, RiskBadge, Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { formatDate } from "@/lib/utils";

const STATUSES = ["Open", "Investigating", "Contained", "Resolved", "Archived"];

export function CaseDetailView({ caseId }: { caseId: string }) {
  const router = useRouter();
  const qc = useQueryClient();
  const [note, setNote] = useState("");

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["case", caseId],
    queryFn: () => api.getCase(caseId),
  });

  const updateStatus = useMutation({
    mutationFn: (status: string) => api.updateCase(caseId, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["case", caseId] }),
  });

  const addNote = useMutation({
    mutationFn: () => api.addCaseNote(caseId, "Analyst", note),
    onSuccess: () => {
      setNote("");
      qc.invalidateQueries({ queryKey: ["case", caseId] });
    },
  });

  const generateReport = useMutation({
    mutationFn: () => api.generateReport(caseId),
    onSuccess: (r) => router.push(`/reports/${r.id}`),
  });

  if (isLoading) return <LoadingState label="Loading case..." />;
  if (isError || !data) return <ErrorState onRetry={refetch} />;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="mono text-xs text-[var(--text-faint)]">{data.case_number}</span>
            <SeverityBadge severity={data.severity} />
          </div>
          <h2 className="text-lg font-semibold text-[var(--text)]">{data.title}</h2>
          <p className="text-sm text-[var(--text-muted)] mt-1 max-w-2xl">{data.summary}</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={data.status} onValueChange={(v) => updateStatus.mutate(v)}>
            <SelectTrigger className="w-40"><SelectValue /></SelectTrigger>
            <SelectContent>
              {STATUSES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
            </SelectContent>
          </Select>
          <Button size="sm" onClick={() => generateReport.mutate()} disabled={generateReport.isPending || data.emails.length === 0}>
            <FileText size={14} /> {generateReport.isPending ? "Generating..." : "Generate Report"}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><MailIcon size={14} /> Linked Emails ({data.emails.length})</CardTitle></CardHeader>
          <CardContent className="flex flex-col gap-1 p-2">
            {data.emails.length === 0 ? <EmptyState title="No emails linked" /> : data.emails.map((e) => (
              <button
                key={e.id}
                onClick={() => router.push(`/analyzer/${e.id}`)}
                className="flex items-center justify-between gap-2 rounded-md px-3 py-2 hover:bg-[var(--surface-hover)] text-left"
              >
                <div className="min-w-0">
                  <p className="text-sm text-[var(--text)] truncate">{e.subject}</p>
                  <p className="text-xs text-[var(--text-muted)] truncate">{e.from_addr}</p>
                </div>
                {e.severity && <SeverityBadge severity={e.severity} />}
              </button>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><ShieldCheck size={14} /> Evidence ({data.evidence.length})</CardTitle></CardHeader>
          <CardContent className="flex flex-col gap-2 p-3">
            {data.evidence.length === 0 ? <EmptyState title="No evidence" /> : data.evidence.map((ev) => (
              <div key={ev.id} className="rounded-md border border-[var(--border)] bg-[var(--bg-elevated)] p-2.5 text-xs">
                <p className="text-[var(--text)] font-medium truncate">{ev.filename}</p>
                <p className="mono text-[var(--text-faint)] truncate mt-0.5">{ev.sha256}</p>
                <div className="flex items-center justify-between mt-1">
                  <Badge variant={ev.integrity_status === "VERIFIED" ? "soft" : "outline"}>{ev.integrity_status}</Badge>
                  <span className="text-[var(--text-faint)]">{formatDate(ev.created_at)}</span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Indicators ({data.iocs.length})</CardTitle></CardHeader>
          <CardContent className="flex flex-col gap-1.5 p-3 max-h-64 overflow-y-auto scrollbar-thin">
            {data.iocs.length === 0 ? <EmptyState title="No IOCs" /> : data.iocs.map((i, idx) => (
              <div key={idx} className="flex items-center justify-between text-xs">
                <span className="mono text-[var(--text-muted)] truncate pr-2">{i.value}</span>
                <RiskBadge risk={i.risk} />
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Forensic Timeline</CardTitle></CardHeader>
        <CardContent>
          {data.timeline.length === 0 ? <EmptyState title="No timeline events yet" /> : (
            <div className="relative pl-6">
              <div className="absolute left-[9px] top-1 bottom-1 w-px bg-[var(--border-strong)]" />
              <div className="flex flex-col gap-4">
                {data.timeline.map((t, i) => (
                  <div key={i} className="relative">
                    <div className="absolute -left-6 top-0.5 text-[var(--accent)]"><CheckCircle2 size={14} /></div>
                    <p className="text-sm text-[var(--text)]">{t.description}</p>
                    <p className="text-xs text-[var(--text-faint)]">{t.event_type.replace(/_/g, " ")} · {formatDate(t.occurred_at)}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Analyst Notes</CardTitle></CardHeader>
        <CardContent className="flex flex-col gap-3">
          {data.notes.length > 0 && (
            <div className="flex flex-col gap-2 mb-2">
              {data.notes.map((n, i) => (
                <div key={i} className="rounded-md bg-[var(--bg-elevated)] border border-[var(--border)] p-2.5 text-sm">
                  <p className="text-[var(--text)]">{n.text}</p>
                  <p className="text-xs text-[var(--text-faint)] mt-1">{n.author} · {formatDate(n.created_at)}</p>
                </div>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <Textarea rows={2} placeholder="Add investigation note..." value={note} onChange={(e) => setNote(e.target.value)} />
            <Button onClick={() => addNote.mutate()} disabled={!note.trim() || addNote.isPending} className="self-start">Add</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
