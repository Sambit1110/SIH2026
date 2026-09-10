"use client";

import { useState } from "react";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";
import { RiskBadge } from "@/components/ui/badge";
import { EmptyState } from "@/components/shared/States";
import type { Ioc } from "@/lib/api";

const TYPE_LABELS: Record<string, string> = {
  ip: "IP Address", domain: "Domain", url: "URL", email: "Email Address",
  hash: "Attachment Hash", message_id: "Message-ID", mx: "MX Host",
};

export function IocTable({ iocs }: { iocs: Ioc[] }) {
  const [filter, setFilter] = useState<string>("all");
  const types = ["all", ...Array.from(new Set(iocs.map((i) => i.type)))];
  const filtered = filter === "all" ? iocs : iocs.filter((i) => i.type === filter);

  if (iocs.length === 0) return <EmptyState title="No indicators extracted" />;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-1.5 flex-wrap">
        {types.map((t) => (
          <button
            key={t}
            onClick={() => setFilter(t)}
            className="rounded-full px-2.5 py-1 text-[11px] transition-colors"
            style={{
              background: filter === t ? "var(--accent-soft)" : "var(--surface-active)",
              color: filter === t ? "var(--accent)" : "var(--text-muted)",
            }}
          >
            {t === "all" ? "All" : TYPE_LABELS[t] ?? t} {t !== "all" && `(${iocs.filter((i) => i.type === t).length})`}
          </button>
        ))}
      </div>
      <Table>
        <THead>
          <TR>
            <TH>Type</TH>
            <TH>Value</TH>
            <TH>Risk</TH>
            <TH>Confidence</TH>
            <TH>Source</TH>
          </TR>
        </THead>
        <TBody>
          {filtered.map((ioc) => (
            <TR key={ioc.id}>
              <TD className="text-[var(--text-muted)]">{TYPE_LABELS[ioc.type] ?? ioc.type}</TD>
              <TD className="mono max-w-[320px] truncate" title={ioc.value}>{ioc.value}</TD>
              <TD><RiskBadge risk={ioc.risk} /></TD>
              <TD className="mono text-[var(--text-muted)]">{Math.round(ioc.confidence * 100)}%</TD>
              <TD className="text-[var(--text-muted)] text-xs">{ioc.source}</TD>
            </TR>
          ))}
        </TBody>
      </Table>
    </div>
  );
}
