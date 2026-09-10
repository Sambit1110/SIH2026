"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ShieldAlert } from "lucide-react";
import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "./nav-items";

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="no-print hidden md:flex w-60 shrink-0 flex-col border-r border-[var(--border)] bg-[var(--bg-elevated)]">
      <div className="flex items-center gap-2 px-5 h-16 border-b border-[var(--border)]">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-[var(--accent-soft)] text-[var(--accent)]">
          <ShieldAlert size={18} strokeWidth={2.25} />
        </div>
        <div className="leading-tight">
          <div className="font-semibold text-[var(--text)] tracking-tight text-sm">TRACE-X</div>
          <div className="text-[10px] text-[var(--text-faint)] uppercase tracking-wider">Forensic Intelligence</div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto py-3 px-2 scrollbar-thin">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || pathname?.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm mb-0.5 transition-colors",
                active
                  ? "bg-[var(--surface-active)] text-[var(--text)]"
                  : "text-[var(--text-muted)] hover:bg-[var(--surface-hover)] hover:text-[var(--text)]",
              )}
            >
              <Icon size={16} strokeWidth={2} className={active ? "text-[var(--accent)]" : ""} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="p-3 border-t border-[var(--border)]">
        <div className="rounded-md bg-[var(--surface)] px-3 py-2.5 text-xs text-[var(--text-muted)]">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[var(--text-faint)] uppercase tracking-wide text-[10px]">Build</span>
            <span className="text-[var(--low)]">SIH 2026 Prototype</span>
          </div>
          <p className="text-[var(--text-faint)] leading-snug">
            Investigative intelligence, not legal attribution.
          </p>
        </div>
      </div>
    </aside>
  );
}
