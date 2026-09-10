"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { UploadCloud, ClipboardPaste, FlaskConical, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { SeverityBadge } from "@/components/ui/badge";
import { LoadingState, EmptyState } from "@/components/shared/States";
import { timeAgo } from "@/lib/utils";

const DEMO_CASE_LABELS: Record<string, string> = {
  "case-01": "CEO Impersonation / BEC",
  "case-02": "Credential Phishing",
  "case-03": "Vendor Invoice Fraud",
  "case-04": "Legitimate Institutional Email",
  "case-05": "Lookalike Domain Attack",
  "case-06": "Phishing Campaign - Second Wave",
};

export default function AnalyzerLandingPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [rawEmail, setRawEmail] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: emails, isLoading } = useQuery({ queryKey: ["emails"], queryFn: api.listEmails });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.uploadEmail(file),
    onSuccess: (res) => router.push(`/analyzer/${res.email_id}`),
    onError: (e: Error) => setError(e.message),
  });

  const analyzeMutation = useMutation({
    mutationFn: (raw: string) => api.analyzeRawEmail(raw),
    onSuccess: (res) => router.push(`/analyzer/${res.email_id}`),
    onError: (e: Error) => setError(e.message),
  });

  const demoCases = (emails ?? []).filter((e) => e.label === "Demo");
  const uploaded = (emails ?? []).filter((e) => e.label !== "Demo").sort((a, b) => b.created_at.localeCompare(a.created_at));

  const isBusy = uploadMutation.isPending || analyzeMutation.isPending;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold text-[var(--text)]">Email Analyzer</h2>
        <p className="text-sm text-[var(--text-muted)]">Upload a .eml file, paste raw source, or open a seeded demo case to run the full DETECT pipeline.</p>
      </div>

      {error && (
        <div className="rounded-md border border-[var(--critical)] bg-[var(--critical-soft)] px-4 py-2.5 text-sm text-[var(--critical)]">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Upload .EML File</CardTitle>
            <CardDescription>Max 10MB. Attachments are never executed — metadata only.</CardDescription>
          </CardHeader>
          <CardContent>
            <div
              onClick={() => !isBusy && fileInputRef.current?.click()}
              className="flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-[var(--border-strong)] py-10 cursor-pointer hover:border-[var(--accent)] transition-colors"
            >
              {uploadMutation.isPending ? (
                <Loader2 className="animate-spin text-[var(--accent)]" size={26} />
              ) : (
                <UploadCloud className="text-[var(--text-faint)]" size={26} />
              )}
              <p className="text-sm text-[var(--text-muted)]">Click to select a .eml or .txt file</p>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".eml,.txt"
              className="hidden"
              onChange={(e) => {
                setError(null);
                const file = e.target.files?.[0];
                if (file) uploadMutation.mutate(file);
              }}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Paste Raw Email Source</CardTitle>
            <CardDescription>Full RFC 5322 source including headers.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Textarea
              rows={6}
              placeholder="From: attacker@example.com&#10;To: victim@company.com&#10;Subject: ...&#10;&#10;Body..."
              value={rawEmail}
              onChange={(e) => setRawEmail(e.target.value)}
            />
            <Button
              onClick={() => { setError(null); analyzeMutation.mutate(rawEmail); }}
              disabled={!rawEmail.trim() || isBusy}
              className="self-start"
            >
              <ClipboardPaste size={14} /> {analyzeMutation.isPending ? "Analyzing..." : "Analyze"}
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><FlaskConical size={15} /> Seeded Demo Cases</CardTitle>
          <CardDescription>Deterministic synthetic cases — no external network calls required.</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? <LoadingState /> : demoCases.length === 0 ? <EmptyState title="No demo cases seeded" /> : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {demoCases.map((e) => (
                <button
                  key={e.id}
                  onClick={() => router.push(`/analyzer/${e.id}`)}
                  className="text-left rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] p-4 hover:border-[var(--accent)] transition-colors"
                >
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs uppercase tracking-wide text-[var(--text-faint)]">
                      {DEMO_CASE_LABELS[e.demo_case_key ?? ""] ?? e.demo_case_key}
                    </span>
                    {e.severity && <SeverityBadge severity={e.severity} />}
                  </div>
                  <p className="text-sm font-medium text-[var(--text)] truncate">{e.subject}</p>
                  <p className="text-xs text-[var(--text-muted)] mt-1 truncate">{e.from_addr}</p>
                  {e.overall_score != null && <p className="text-xs text-[var(--text-faint)] mt-2 mono">Risk score: {e.overall_score}/100</p>}
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {uploaded.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Recently Analyzed</CardTitle></CardHeader>
          <CardContent className="flex flex-col gap-1 p-2">
            {uploaded.map((e) => (
              <button
                key={e.id}
                onClick={() => router.push(`/analyzer/${e.id}`)}
                className="flex items-center justify-between gap-3 rounded-md px-3 py-2.5 hover:bg-[var(--surface-hover)] transition-colors text-left"
              >
                <div className="min-w-0">
                  <p className="text-sm text-[var(--text)] truncate">{e.subject || "(no subject)"}</p>
                  <p className="text-xs text-[var(--text-muted)] truncate">{e.from_addr} · {timeAgo(e.created_at)}</p>
                </div>
                {e.severity && <SeverityBadge severity={e.severity} />}
              </button>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
