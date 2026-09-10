"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { RefreshCw, Share2 } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { LoadingState, ErrorState, EmptyState } from "@/components/shared/States";

export default function CampaignsPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["campaigns"], queryFn: api.listCampaigns });

  const recompute = useMutation({
    mutationFn: api.recomputeCampaigns,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campaigns"] }),
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-lg font-semibold text-[var(--text)]">Campaign Correlation</h2>
          <p className="text-sm text-[var(--text-muted)]">Emails grouped by shared domains, IPs, or URLs — deterministic connected-components correlation.</p>
        </div>
        <Button variant="secondary" size="sm" onClick={() => recompute.mutate()} disabled={recompute.isPending}>
          <RefreshCw size={14} className={recompute.isPending ? "animate-spin" : ""} /> Recompute
        </Button>
      </div>

      {isLoading ? <LoadingState /> : isError ? <ErrorState onRetry={refetch} /> : !data || data.length === 0 ? (
        <EmptyState
          icon={Share2}
          title="No correlated campaigns found"
          description="Campaigns emerge automatically once two or more analyzed emails share a domain, IP, or URL indicator."
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {data.map((c) => (
            <Card key={c.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>{c.campaign_number}</CardTitle>
                  <Badge variant="soft">{c.confidence}% confidence</Badge>
                </div>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <p className="text-sm text-[var(--text)]">{c.name}</p>
                <div className="grid grid-cols-3 gap-3 text-xs">
                  <Stat label="Related Emails" value={c.related_emails.length} />
                  <Stat label="Domains" value={c.shared_indicators.domains.length} />
                  <Stat label="IPs" value={c.shared_indicators.ips.length} />
                </div>
                <div>
                  <p className="text-[var(--text-faint)] uppercase text-[10px] tracking-wide mb-1">Primary Technique</p>
                  <p className="text-sm text-[var(--text)]">{c.technique}</p>
                </div>
                <div className="flex flex-col gap-1">
                  {c.related_emails.map((e) => (
                    <button
                      key={e.id}
                      onClick={() => router.push(`/analyzer/${e.id}`)}
                      className="text-left text-xs text-[var(--text-muted)] hover:text-[var(--accent)] truncate"
                    >
                      → {e.subject}
                    </button>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md bg-[var(--bg-elevated)] border border-[var(--border)] px-2 py-1.5 text-center">
      <div className="text-sm font-semibold text-[var(--text)]">{value}</div>
      <div className="text-[10px] text-[var(--text-faint)] uppercase">{label}</div>
    </div>
  );
}
