"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { LoadingState, ErrorState, EmptyState } from "@/components/shared/States";
import { GraphView } from "@/components/graph/GraphView";
import { GeoMap } from "@/components/map/GeoMap";

export default function InfrastructurePage() {
  const [selectedId, setSelectedId] = useState<string>("");
  const [selectedNode, setSelectedNode] = useState<{ id: string; data: Record<string, unknown> } | null>(null);

  const { data: emails, isLoading: loadingList } = useQuery({ queryKey: ["emails"], queryFn: api.listEmails });
  const emailId = selectedId || emails?.[0]?.id || "";

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["email-full", emailId],
    queryFn: () => api.getEmailFull(emailId),
    enabled: !!emailId,
  });

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-lg font-semibold text-[var(--text)]">Infrastructure Intelligence</h2>
          <p className="text-sm text-[var(--text-muted)]">Relationship graph and observed geolocation for a selected analyzed email.</p>
        </div>
        {!loadingList && emails && emails.length > 0 && (
          <Select value={emailId} onValueChange={setSelectedId}>
            <SelectTrigger className="w-80"><SelectValue placeholder="Select an analyzed email" /></SelectTrigger>
            <SelectContent>
              {emails.map((e) => <SelectItem key={e.id} value={e.id}>{e.subject || e.id}</SelectItem>)}
            </SelectContent>
          </Select>
        )}
      </div>

      {loadingList ? <LoadingState /> : !emails || emails.length === 0 ? (
        <EmptyState title="No analyzed emails yet" description="Analyze an email first to explore its infrastructure." />
      ) : isLoading ? <LoadingState /> : isError || !data ? <ErrorState onRetry={refetch} /> : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <Card className="h-[520px]">
            <CardHeader><CardTitle>Relationship Graph</CardTitle></CardHeader>
            <CardContent className="p-0 h-[460px]">
              <GraphView graph={data.graph} onSelectNode={(id, d) => setSelectedNode({ id, data: d })} />
            </CardContent>
          </Card>
          <Card className="h-[520px]">
            <CardHeader><CardTitle>Observed Geolocation</CardTitle></CardHeader>
            <CardContent className="p-0 h-[460px]">
              <GeoMap hops={data.trace} />
            </CardContent>
          </Card>
          {selectedNode && (
            <Card className="xl:col-span-2">
              <CardHeader><CardTitle>Node Inspector — {selectedNode.id}</CardTitle></CardHeader>
              <CardContent>
                <pre className="text-xs mono text-[var(--text-muted)] whitespace-pre-wrap break-all">
                  {JSON.stringify(selectedNode.data, null, 2)}
                </pre>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
