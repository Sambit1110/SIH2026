"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { AlertOctagon, FlameKindling, FolderOpen, Fingerprint, Share2, Mail } from "lucide-react";
import { AreaChart, Area, ResponsiveContainer, XAxis, YAxis, Tooltip as RTooltip } from "recharts";
import { api } from "@/lib/api";
import { MetricCard } from "@/components/shared/MetricCard";
import { LoadingState, ErrorState, EmptyState } from "@/components/shared/States";
import { SeverityBadge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { timeAgo } from "@/lib/utils";

export default function OverviewPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["dashboard"],
    queryFn: api.dashboard,
  });

  if (isLoading) return <LoadingState label="Loading dashboard..." />;
  if (isError || !data) return <ErrorState message="Could not reach the Trace-X backend." onRetry={refetch} />;

  const maxDist = Math.max(1, ...data.threat_distribution.map((d) => d.count));

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-lg font-semibold text-[var(--text)]">Security Operations Overview</h2>
        <p className="text-sm text-[var(--text-muted)]">
          DETECT → TRACE → CORRELATE → INVESTIGATE → REPORT — current platform state.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        <MetricCard label="Emails Analyzed" value={data.metrics.emails_analyzed} icon={Mail} colorVar="--info" />
        <MetricCard label="Critical Threats" value={data.metrics.critical_threats} icon={AlertOctagon} colorVar="--critical" />
        <MetricCard label="High-Risk Threats" value={data.metrics.high_risk_threats} icon={FlameKindling} colorVar="--high" />
        <MetricCard label="Active Investigations" value={data.metrics.active_investigations} icon={FolderOpen} colorVar="--accent" />
        <MetricCard label="IOC Count" value={data.metrics.ioc_count} icon={Fingerprint} colorVar="--medium" />
        <MetricCard label="Campaigns" value={data.metrics.campaign_count} icon={Share2} colorVar="--low" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Threat Activity Timeline</CardTitle>
          </CardHeader>
          <CardContent className="h-56">
            {data.threat_activity_timeline.length === 0 ? (
              <EmptyState title="No activity yet" description="Analyze an email to populate the timeline." />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.threat_activity_timeline}>
                  <defs>
                    <linearGradient id="activityFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="date" tick={{ fill: "var(--text-faint)", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, (max: number) => Math.max(4, max + 2)]} hide />
                  <RTooltip
                    contentStyle={{ background: "var(--surface)", border: "1px solid var(--border-strong)", borderRadius: 8, fontSize: 12 }}
                    labelStyle={{ color: "var(--text-muted)" }}
                  />
                  <Area type="monotone" dataKey="events" stroke="var(--accent)" fill="url(#activityFill)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Threat Type Distribution</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {data.threat_distribution.length === 0 ? (
              <EmptyState title="No classifications yet" />
            ) : (
              data.threat_distribution.map((d) => (
                <div key={d.classification}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-[var(--text-muted)] truncate pr-2">{d.classification}</span>
                    <span className="text-[var(--text)] font-medium">{d.count}</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-[var(--surface-active)] overflow-hidden">
                    <div
                      className="h-full rounded-full bg-[var(--accent)]"
                      style={{ width: `${(d.count / maxDist) * 100}%` }}
                    />
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Recent High-Severity Alerts</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-1 p-2">
            {data.recent_alerts.length === 0 ? (
              <EmptyState title="No critical or high-severity alerts" description="All clear for now." />
            ) : (
              data.recent_alerts.map((a) => (
                <Link
                  key={a.id}
                  href={`/analyzer/${a.id}`}
                  className="flex items-center justify-between gap-3 rounded-md px-3 py-2.5 hover:bg-[var(--surface-hover)] transition-colors"
                >
                  <div className="min-w-0">
                    <p className="text-sm text-[var(--text)] truncate">{a.subject}</p>
                    <p className="text-xs text-[var(--text-muted)] truncate">{a.from_addr} · {a.classification}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs mono text-[var(--text-muted)]">{a.overall_score}</span>
                    <SeverityBadge severity={a.severity} />
                  </div>
                </Link>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Investigations</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-1 p-2">
            {data.recent_investigations.length === 0 ? (
              <EmptyState title="No investigations yet" />
            ) : (
              data.recent_investigations.map((c) => (
                <Link
                  key={c.id}
                  href={`/investigations/${c.id}`}
                  className="flex items-center justify-between gap-3 rounded-md px-3 py-2.5 hover:bg-[var(--surface-hover)] transition-colors"
                >
                  <div className="min-w-0">
                    <p className="text-sm text-[var(--text)] truncate">{c.title}</p>
                    <p className="text-xs text-[var(--text-muted)]">{c.case_number} · {c.status} · {timeAgo(c.updated_at)}</p>
                  </div>
                  <SeverityBadge severity={c.severity} />
                </Link>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
