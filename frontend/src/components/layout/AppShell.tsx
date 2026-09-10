"use client";

import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[var(--bg)] text-[var(--text)]">
      <Sidebar />
      <div className="flex flex-1 flex-col min-w-0">
        <Topbar />
        <main className="flex-1 overflow-y-auto scrollbar-thin">
          <div className="mx-auto max-w-[1600px] p-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
