"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ShieldCheck, ShieldAlert, ShieldQuestion } from "lucide-react";
import { api } from "@/lib/api";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { LoadingState, ErrorState, EmptyState } from "@/components/shared/States";
import { formatDate } from "@/lib/utils";

export default function EvidencePage() {
  const qc = useQueryClient();
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["evidence"], queryFn: api.listEvidence });

  const verify = useMutation({
    mutationFn: (id: string) => api.verifyEvidence(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["evidence"] }),
  });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold text-[var(--text)]">Evidence & Chain of Custody</h2>
        <p className="text-sm text-[var(--text-muted)]">
          Every uploaded or seeded email is preserved with a SHA-256 hash captured at ingestion. Attachments are
          never executed — metadata only.
        </p>
      </div>

      {isLoading ? <LoadingState /> : isError ? <ErrorState onRetry={refetch} /> : !data || data.length === 0 ? (
        <EmptyState icon={ShieldCheck} title="No evidence recorded yet" />
      ) : (
        <Table>
          <THead>
            <TR><TH>Filename</TH><TH>SHA-256</TH><TH>Acquisition</TH><TH>Integrity</TH><TH>Captured</TH><TH></TH></TR>
          </THead>
          <TBody>
            {data.map((e) => (
              <TR key={e.id}>
                <TD className="text-[var(--text)]">{e.filename}</TD>
                <TD className="mono text-xs text-[var(--text-muted)] max-w-[220px] truncate" title={e.sha256}>{e.sha256}</TD>
                <TD className="text-[var(--text-muted)] text-xs">{e.acquisition_method}</TD>
                <TD>
                  <Badge variant={e.integrity_status === "VERIFIED" ? "soft" : "outline"}>
                    {e.integrity_status === "VERIFIED" ? <ShieldCheck size={11} /> : e.integrity_status === "TAMPERED" ? <ShieldAlert size={11} /> : <ShieldQuestion size={11} />}
                    {e.integrity_status}
                  </Badge>
                </TD>
                <TD className="text-xs text-[var(--text-muted)]">{formatDate(e.created_at)}</TD>
                <TD>
                  <Button size="sm" variant="ghost" onClick={() => verify.mutate(e.id)} disabled={verify.isPending}>
                    Re-verify
                  </Button>
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}
