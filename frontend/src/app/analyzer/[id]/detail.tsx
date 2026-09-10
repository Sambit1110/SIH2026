"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { FileText, FolderPlus, Paperclip, ExternalLink } from "lucide-react";
import { api } from "@/lib/api";
import { LoadingState, ErrorState } from "@/components/shared/States";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ThreatSummary, ExplanationFactors } from "@/components/analyzer/ThreatSummary";
import { AuthPanel } from "@/components/analyzer/AuthPanel";
import { HeaderForensicsPanel } from "@/components/analyzer/HeaderForensics";
import { IocTable } from "@/components/analyzer/IocTable";
import { RelayTimeline } from "@/components/analyzer/RelayTimeline";
import { AttributionPanel, RecommendedActions } from "@/components/analyzer/AttributionPanel";
import { GraphView } from "@/components/graph/GraphView";
import { GeoMap } from "@/components/map/GeoMap";
import { formatDate } from "@/lib/utils";

export function EmailAnalyzerDetail({ emailId }: { emailId: string }) {
  const router = useRouter();
  const qc = useQueryClient();
  const [selectedNode, setSelectedNode] = useState<{ id: string; data: Record<string, unknown> } | null>(null);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["email-full", emailId],
    queryFn: () => api.getEmailFull(emailId),
  });

  const openInvestigation = useMutation({
    mutationFn: async () => {
      if (!data) throw new Error("no data");
      const { id: caseId } = await api.createCase(
        `Investigation: ${data.email.subject || "Untitled"}`,
        data.threat_analysis?.severity ?? "LOW",
      );
      await api.linkEmailToCase(caseId, emailId);
      return caseId;
    },
    onSuccess: (caseId) => router.push(`/investigations/${caseId}`),
  });

  const generateReport = useMutation({
    mutationFn: async () => {
      if (!data) throw new Error("no data");
      let caseId = data.email.case_id;
      if (!caseId) {
        const created = await api.createCase(`Investigation: ${data.email.subject || "Untitled"}`, data.threat_analysis?.severity ?? "LOW");
        caseId = created.id;
        await api.linkEmailToCase(caseId, emailId);
      }
      const report = await api.generateReport(caseId, emailId);
      return report.id;
    },
    onSuccess: (reportId) => {
      qc.invalidateQueries({ queryKey: ["email-full", emailId] });
      router.push(`/reports/${reportId}`);
    },
  });

  if (isLoading) return <LoadingState label="Loading investigation..." />;
  if (isError || !data) return <ErrorState message="Could not load this email." onRetry={refetch} />;

  const { email, headers, threat_analysis, auth, iocs, trace, graph, evidence } = data;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant={email.label === "Demo" ? "soft" : "outline"}>{email.label === "Demo" ? "Demo Case" : "Uploaded Evidence"}</Badge>
            {email.case_id && <Badge variant="outline">Linked to case</Badge>}
          </div>
          <h2 className="text-lg font-semibold text-[var(--text)] truncate max-w-2xl">{email.subject || "(no subject)"}</h2>
          <p className="text-sm text-[var(--text-muted)] mt-0.5">
            From <span className="mono text-[var(--text)]">{email.from_addr}</span> to <span className="mono text-[var(--text)]">{email.to_addr}</span>
          </p>
          <p className="text-xs text-[var(--text-faint)] mt-1">{formatDate(email.date_header || email.created_at)}</p>
        </div>
        <div className="flex gap-2 shrink-0">
          {email.case_id ? (
            <Button variant="secondary" size="sm" onClick={() => router.push(`/investigations/${email.case_id}`)}>
              <ExternalLink size={14} /> View Case
            </Button>
          ) : (
            <Button variant="secondary" size="sm" onClick={() => openInvestigation.mutate()} disabled={openInvestigation.isPending}>
              <FolderPlus size={14} /> {openInvestigation.isPending ? "Creating..." : "Open Investigation"}
            </Button>
          )}
          <Button size="sm" onClick={() => generateReport.mutate()} disabled={generateReport.isPending}>
            <FileText size={14} /> {generateReport.isPending ? "Generating..." : "Generate Forensic Report"}
          </Button>
        </div>
      </div>

      <Tabs defaultValue="summary">
        <TabsList>
          <TabsTrigger value="summary">Threat Summary</TabsTrigger>
          <TabsTrigger value="auth">Authentication</TabsTrigger>
          <TabsTrigger value="headers">Header Forensics</TabsTrigger>
          <TabsTrigger value="iocs">IOCs ({iocs.length})</TabsTrigger>
          <TabsTrigger value="trace">Relay Trace</TabsTrigger>
          <TabsTrigger value="map">Geolocation</TabsTrigger>
          <TabsTrigger value="graph">Infrastructure Graph</TabsTrigger>
          <TabsTrigger value="attribution">AI Assessment</TabsTrigger>
          <TabsTrigger value="original">Original Email</TabsTrigger>
        </TabsList>

        <TabsContent value="summary">
          {threat_analysis ? (
            <div className="flex flex-col gap-5">
              <Card><CardContent className="pt-5"><ThreatSummary analysis={threat_analysis} /></CardContent></Card>
              <Card>
                <CardHeader><CardTitle>Why this score — contributing factors</CardTitle></CardHeader>
                <CardContent><ExplanationFactors factors={threat_analysis.factors} /></CardContent>
              </Card>
            </div>
          ) : <p className="text-sm text-[var(--text-muted)]">Analysis unavailable.</p>}
        </TabsContent>

        <TabsContent value="auth">
          <Card><CardContent className="pt-5">{auth ? <AuthPanel auth={auth} /> : <p className="text-sm text-[var(--text-muted)]">No authentication data.</p>}</CardContent></Card>
        </TabsContent>

        <TabsContent value="headers">
          <Card><CardContent className="pt-5"><HeaderForensicsPanel findings={headers.findings} rawHeaders={headers.raw_headers} /></CardContent></Card>
        </TabsContent>

        <TabsContent value="iocs">
          <Card><CardContent className="pt-5"><IocTable iocs={iocs} /></CardContent></Card>
        </TabsContent>

        <TabsContent value="trace">
          <Card><CardContent className="pt-5"><RelayTimeline hops={trace} /></CardContent></Card>
        </TabsContent>

        <TabsContent value="map">
          <Card><CardContent className="p-0 h-[480px]"><GeoMap hops={trace} /></CardContent></Card>
        </TabsContent>

        <TabsContent value="graph">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Card className="lg:col-span-2 h-[520px]"><CardContent className="p-0 h-full"><GraphView graph={graph} onSelectNode={(id, d) => setSelectedNode({ id, data: d })} /></CardContent></Card>
            <Card>
              <CardHeader><CardTitle>Node Inspector</CardTitle></CardHeader>
              <CardContent>
                {selectedNode ? (
                  <pre className="text-xs mono text-[var(--text-muted)] whitespace-pre-wrap break-all">
                    {JSON.stringify({ id: selectedNode.id, ...selectedNode.data }, null, 2)}
                  </pre>
                ) : (
                  <p className="text-sm text-[var(--text-muted)]">Click a node to inspect its intelligence.</p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="attribution">
          {threat_analysis ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Card><CardHeader><CardTitle>Attribution Assessment</CardTitle></CardHeader><CardContent><AttributionPanel analysis={threat_analysis} /></CardContent></Card>
              <Card><CardHeader><CardTitle>Recommended Actions</CardTitle></CardHeader><CardContent><RecommendedActions analysis={threat_analysis} /></CardContent></Card>
            </div>
          ) : <p className="text-sm text-[var(--text-muted)]">Analysis unavailable.</p>}
        </TabsContent>

        <TabsContent value="original">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardHeader><CardTitle>Original Evidence Metadata</CardTitle></CardHeader>
              <CardContent className="flex flex-col gap-2 text-sm">
                <Row label="Evidence ID" value={evidence?.id} />
                <Row label="Filename" value={evidence?.filename} />
                <Row label="SHA-256" value={evidence?.sha256} mono />
                <Row label="Integrity" value={evidence?.integrity_status} />
                <Row label="Message-ID" value={email.message_id} mono />
                <Row label="Reply-To" value={email.reply_to} mono />
                <Row label="Return-Path" value={email.return_path} mono />
                {email.attachments.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs uppercase tracking-wide text-[var(--text-faint)] mb-1.5">Attachments (metadata only — never executed)</p>
                    {email.attachments.map((a, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs text-[var(--text-muted)] py-1">
                        <Paperclip size={12} /> {a.filename} · {a.mime} · {a.size}B
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Original Message Body</CardTitle></CardHeader>
              <CardContent>
                <pre className="text-xs mono text-[var(--text-muted)] whitespace-pre-wrap max-h-[400px] overflow-y-auto scrollbar-thin">
                  {email.body_text || email.body_html.replace(/<[^>]+>/g, " ") || "(empty body)"}
                </pre>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value?: string | null; mono?: boolean }) {
  return (
    <div className="flex justify-between gap-4">
      <span className="text-[var(--text-faint)] shrink-0">{label}</span>
      <span className={`text-[var(--text)] text-right break-all ${mono ? "mono text-xs" : ""}`}>{value || "—"}</span>
    </div>
  );
}
