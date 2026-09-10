"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, THead, TBody, TR, TH, TD } from "@/components/ui/table";
import { SeverityBadge, Badge } from "@/components/ui/badge";
import { LoadingState, ErrorState, EmptyState } from "@/components/shared/States";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { formatDate } from "@/lib/utils";

export default function InvestigationsPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [title, setTitle] = useState("");
  const [open, setOpen] = useState(false);

  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["cases"], queryFn: api.listCases });

  const createCase = useMutation({
    mutationFn: () => api.createCase(title),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["cases"] });
      setOpen(false);
      setTitle("");
      router.push(`/investigations/${res.id}`);
    },
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-[var(--text)]">Investigations</h2>
          <p className="text-sm text-[var(--text-muted)]">Case management for grouped evidence, findings, and forensic timelines.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button size="sm"><Plus size={14} /> New Case</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Create Investigation Case</DialogTitle></DialogHeader>
            <div className="flex flex-col gap-3">
              <Input placeholder="Case title" value={title} onChange={(e) => setTitle(e.target.value)} />
              <Button onClick={() => createCase.mutate()} disabled={!title.trim() || createCase.isPending}>
                {createCase.isPending ? "Creating..." : "Create Case"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? <LoadingState /> : isError ? <ErrorState onRetry={refetch} /> : !data || data.length === 0 ? (
        <EmptyState title="No investigations yet" description="Create a case, or open one directly from the Email Analyzer." />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Case</TH><TH>Title</TH><TH>Status</TH><TH>Severity</TH><TH>Analyst</TH>
              <TH>Emails</TH><TH>Updated</TH>
            </TR>
          </THead>
          <TBody>
            {data.map((c) => (
              <TR key={c.id} className="cursor-pointer hover:bg-[var(--surface-hover)]" onClick={() => router.push(`/investigations/${c.id}`)}>
                <TD className="mono text-xs">{c.case_number}</TD>
                <TD className="text-[var(--text)] font-medium">{c.title}</TD>
                <TD><Badge variant="outline">{c.status}</Badge></TD>
                <TD><SeverityBadge severity={c.severity} /></TD>
                <TD className="text-[var(--text-muted)]">{c.analyst}</TD>
                <TD className="text-[var(--text-muted)]">{c.email_count}</TD>
                <TD className="text-[var(--text-muted)] text-xs">{formatDate(c.updated_at)}</TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
    </div>
  );
}
