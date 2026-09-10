import {
  LayoutDashboard, FolderSearch, Mail, Radar, Network,
  Share2, ShieldCheck, FileText, Settings,
} from "lucide-react";

export const NAV_ITEMS = [
  { href: "/overview", label: "Overview", icon: LayoutDashboard },
  { href: "/investigations", label: "Investigations", icon: FolderSearch },
  { href: "/analyzer", label: "Email Analyzer", icon: Mail },
  { href: "/intelligence", label: "Threat Intelligence", icon: Radar },
  { href: "/infrastructure", label: "Infrastructure", icon: Network },
  { href: "/campaigns", label: "Campaigns", icon: Share2 },
  { href: "/evidence", label: "Evidence", icon: ShieldCheck },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/settings", label: "Settings", icon: Settings },
] as const;
