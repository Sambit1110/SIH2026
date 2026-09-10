"use client";

import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { Radio } from "lucide-react";
import { api } from "@/lib/api";
import { NAV_ITEMS } from "./nav-items";

export function Topbar() {
  const pathname = usePathname();
  const current = NAV_ITEMS.find((i) => pathname === i.href || pathname?.startsWith(i.href + "/"));

  const { data } = useQuery({
    queryKey: ["settings"],
    queryFn: api.getSettings,
    staleTime: 60_000,
  });

  const isDemo = (data?.intel_mode ?? "demo") === "demo";

  return (
    <header className="no-print flex items-center justify-between h-16 px-6 border-b border-[var(--border)] bg-[var(--bg-elevated)]/80 backdrop-blur">
      <div>
        <h1 className="text-sm font-semibold text-[var(--text)]">{current?.label ?? "Trace-X"}</h1>
      </div>
      <div className="flex items-center gap-3">
        <div
          className="flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium"
          style={{
            borderColor: isDemo ? "var(--border-strong)" : "var(--low)",
            color: isDemo ? "var(--text-muted)" : "var(--low)",
            background: isDemo ? "var(--surface)" : "var(--low-soft)",
          }}
          title={isDemo ? "Intelligence lookups use deterministic demo data — no external network calls." : "Live intelligence providers enabled, with automatic demo fallback on failure."}
        >
          <Radio size={11} />
          {isDemo ? "Demo Intelligence Mode" : "Live Intelligence Mode"}
        </div>
      </div>
    </header>
  );
}
