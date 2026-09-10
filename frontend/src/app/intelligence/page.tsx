"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { api } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";
import { RiskBadge, Badge } from "@/components/ui/badge";
import { LoadingState, ErrorState, EmptyState } from "@/components/shared/States";

function isIp(value: string) {
  return /^\d{1,3}(\.\d{1,3}){3}$/.test(value.trim());
}

export default function IntelligencePage() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);

  const { data: iocs, isLoading, isError, refetch } = useQuery({ queryKey: ["all-iocs"], queryFn: api.listIocs });

  const lookup = useMutation({
    mutationFn: () => (isIp(query) ? api.lookupIp(query.trim()) : api.lookupDomain(query.trim())),
    onSuccess: setResult,
  });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold text-[var(--text)]">Threat Intelligence</h2>
        <p className="text-sm text-[var(--text-muted)]">Look up any observed IP address or domain, or browse all extracted indicators.</p>
      </div>

      <Card>
        <CardHeader><CardTitle>IP / Domain Lookup</CardTitle></CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex gap-2">
            <Input
              placeholder="e.g. 193.106.31.98 or microsoft-verify-account.xyz"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && query.trim() && lookup.mutate()}
            />
            <Button onClick={() => lookup.mutate()} disabled={!query.trim() || lookup.isPending}>
              <Search size={14} /> {lookup.isPending ? "Looking up..." : "Lookup"}
            </Button>
          </div>
          {result && (
            <div className="rounded-md border border-[var(--border)] bg-[var(--bg-elevated)] p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="mono text-sm text-[var(--text)]">{String(result.ip ?? result.domain)}</span>
                <Badge variant="outline">{String(result.source)}</Badge>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-1.5 text-xs">
                {Object.entries(result).filter(([k]) => !["ip", "domain", "source", "cached"].includes(k)).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-2">
                    <span className="text-[var(--text-faint)] uppercase tracking-wide">{k.replace(/_/g, " ")}</span>
                    <span className="text-[var(--text)] text-right break-all">{Array.isArray(v) ? v.join(", ") || "—" : String(v ?? "—")}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>All Extracted Indicators</CardTitle></CardHeader>
        <CardContent>
          {isLoading ? <LoadingState /> : isError ? <ErrorState onRetry={refetch} /> : !iocs || iocs.length === 0 ? (
            <EmptyState title="No indicators extracted yet" />
          ) : (
            <Table>
              <THead><TR><TH>Type</TH><TH>Value</TH><TH>Risk</TH><TH>Confidence</TH><TH>Source</TH></TR></THead>
              <TBody>
                {iocs.slice(0, 100).map((i) => (
                  <TR key={i.id}>
                    <TD className="text-[var(--text-muted)]">{i.type}</TD>
                    <TD className="mono">{i.value}</TD>
                    <TD><RiskBadge risk={i.risk} /></TD>
                    <TD className="mono text-[var(--text-muted)]">{Math.round(i.confidence * 100)}%</TD>
                    <TD className="text-xs text-[var(--text-muted)]">{i.source}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
