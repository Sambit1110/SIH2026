"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingState } from "@/components/shared/States";

export default function SettingsPage() {
  const { data, isLoading } = useQuery({ queryKey: ["settings"], queryFn: api.getSettings });

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <div>
        <h2 className="text-lg font-semibold text-[var(--text)]">Settings</h2>
        <p className="text-sm text-[var(--text-muted)]">Platform configuration and intelligence provider mode.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Intelligence Mode</CardTitle>
          <CardDescription>Controlled by the backend&apos;s INTEL_MODE environment variable.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {isLoading ? <LoadingState /> : (
            <>
              <div className="flex items-center gap-2">
                <Badge variant="soft">{data?.intel_mode === "live" ? "Live" : "Demo"}</Badge>
                <span className="text-sm text-[var(--text-muted)]">
                  {data?.intel_mode === "live"
                    ? "Live IP geolocation/hosting (ip-api.com), domain registration (RDAP), and DNS MX/SPF lookups are attempted for every newly observed IP or domain, with automatic fallback to demo data only when a lookup genuinely fails. No live reputation/blacklist check is wired up yet, so reputation stays \"Unknown\" for live results."
                    : "All IP and domain intelligence comes from a deterministic, versioned demo dataset. No external network calls are made."}
                </span>
              </div>
              <p className="text-xs text-[var(--text-faint)]">
                To enable live mode, set <code className="mono">INTEL_MODE=live</code> in the backend environment and restart the server.
              </p>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>About Trace-X</CardTitle></CardHeader>
        <CardContent className="flex flex-col gap-2 text-sm text-[var(--text-muted)]">
          <p>AI-Powered Email Threat Detection, GeoLocation and Forensic Intelligence Platform — SIH 2026 prototype.</p>
          <p className="text-xs text-[var(--text-faint)]">
            IP geolocation and infrastructure correlation indicate observed technical infrastructure only,
            not the physical identity or location of any individual. All classifications and attribution
            assessments are investigative leads, not legal findings.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
