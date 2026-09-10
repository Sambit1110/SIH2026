"use client";

import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";
import { LoadingState, ErrorState, EmptyState } from "@/components/shared/States";
import { FileText } from "lucide-react";
import { formatDate } from "@/lib/utils";

interface ReportListItem { id: string; case_id: string; email_id: string; generated_at: string }

export default function ReportsPage() {
  const router = useRouter();
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["reports"],
    queryFn: () => apiGet<ReportListItem[]>("/api/v1/reports"),
  });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold text-[var(--text)]">Forensic Reports</h2>
        <p className="text-sm text-[var(--text-muted)]">Structured, exportable reports generated from completed investigations.</p>
      </div>

      {isLoading ? <LoadingState /> : isError ? <ErrorState onRetry={refetch} /> : !data || data.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No reports generated yet"
          description="Open an analyzed email or investigation and click Generate Forensic Report."
        />
      ) : (
        <Table>
          <THead><TR><TH>Report ID</TH><TH>Case</TH><TH>Generated</TH></TR></THead>
          <TBody>
            {data.map((r) => (
              <TR key={r.id} className="cursor-pointer hover:bg-[var(--surface-hover)]" onClick={() => router.push(`/reports/${r.id}`)}>
                <TD className="mono text-xs">{r.id}</TD>
                <TD className="mono text-xs text-[var(--text-muted)]">{r.case_id}</TD>
                <TD className="text-xs text-[var(--text-muted)]">{formatDate(r.generated_at)}</TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}
