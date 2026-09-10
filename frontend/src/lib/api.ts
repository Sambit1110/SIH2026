const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore body parse failure
    }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  return handle<T>(res);
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  return handle<T>(res);
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return handle<T>(res);
}

export async function apiUpload<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}${path}`, { method: "POST", body: form });
  return handle<T>(res);
}

// ---- Domain types (loosely typed to match the backend's JSON shapes) ----

export interface EmailSummary {
  id: string;
  case_id: string | null;
  from_addr: string;
  to_addr: string;
  subject: string;
  date_header: string;
  label: string;
  demo_case_key: string | null;
  created_at: string;
  overall_score: number | null;
  severity: string | null;
  classification: string | null;
}

export interface ThreatFactor {
  label: string;
  points: number;
  category: string;
  reason: string;
}

export interface ThreatAnalysis {
  overall_score: number;
  severity: string;
  classification: string;
  confidence: number;
  sub_scores: Record<string, number>;
  factors: ThreatFactor[];
  lookalike_findings: Array<{
    observed_domain: string; target_brand: string; similarity: number;
    reason: string; confidence: string;
  }>;
  attribution: {
    conclusion: string; confidence: string; evidence_strength: string;
    supporting_indicators: string[]; limitations: string;
  };
}

export interface AuthResult {
  spf: string; dkim: string; dmarc: string;
  alignment: Record<string, boolean>;
  source: string; raw_auth_header: string;
}

export interface HeaderFinding { issue: string; severity: string; detail: string }

export interface Ioc {
  id: string; type: string; value: string; risk: string;
  confidence: number; source: string; extra: Record<string, unknown>;
}

export interface RelayHop {
  sequence: number; hostname: string; ip: string | null; timestamp: string | null;
  org: string | null; confidence: string; evidence_source: string; flags: string[];
  is_earliest_reliable: boolean;
  geo: {
    country: string; region: string; city: string; lat: number | null; lon: number | null;
    isp: string; asn: string; org: string; reputation: string; source: string;
  } | null;
}

export interface GraphData {
  nodes: Array<{ id: string; type: string; label: string; risk: string; data: Record<string, unknown> }>;
  edges: Array<{ id: string; source: string; target: string; relation: string }>;
}

export interface EmailFull {
  email: {
    id: string; case_id: string | null; from_addr: string; to_addr: string; cc_addr: string;
    reply_to: string; return_path: string; subject: string; date_header: string; message_id: string;
    body_text: string; body_html: string; attachments: Array<{ filename: string; size: number; mime: string; sha256: string }>;
    label: string; demo_case_key: string | null; created_at: string; evidence_id: string | null;
  };
  headers: { raw_headers: Array<{ name: string; value: string }>; findings: HeaderFinding[] };
  threat_analysis: ThreatAnalysis | null;
  auth: AuthResult | null;
  iocs: Ioc[];
  trace: RelayHop[];
  graph: GraphData;
  evidence: {
    id: string; filename: string; sha256: string; size_bytes: number;
    acquisition_method: string; integrity_status: string; created_at: string;
  } | null;
}

export interface DashboardSummary {
  intel_mode: string;
  metrics: {
    emails_analyzed: number; critical_threats: number; high_risk_threats: number;
    active_investigations: number; ioc_count: number; campaign_count: number; total_cases: number;
  };
  threat_distribution: Array<{ classification: string; count: number }>;
  severity_distribution: Array<{ severity: string; count: number }>;
  recent_alerts: Array<{
    id: string; subject: string; from_addr: string; severity: string;
    overall_score: number; classification: string; created_at: string;
  }>;
  recent_investigations: Array<{
    id: string; case_number: string; title: string; status: string; severity: string; updated_at: string;
  }>;
  threat_activity_timeline: Array<{ date: string; events: number }>;
}

export interface CaseSummary {
  id: string; case_number: string; title: string; status: string; severity: string;
  analyst: string; created_at: string; updated_at: string; email_count: number; evidence_count: number;
}

export interface CaseDetail {
  id: string; case_number: string; title: string; status: string; severity: string;
  analyst: string; summary: string; notes: Array<{ author: string; text: string; created_at: string }>;
  created_at: string; updated_at: string;
  emails: Array<{ id: string; subject: string; from_addr: string; overall_score: number | null; severity: string | null; classification: string | null }>;
  evidence: Array<{ id: string; filename: string; sha256: string; integrity_status: string; created_at: string }>;
  iocs: Array<{ type: string; value: string; risk: string }>;
  timeline: Array<{ event_type: string; description: string; occurred_at: string }>;
}

export interface Campaign {
  id: string; campaign_number: string; name: string; technique: string; confidence: number;
  shared_indicators: { domains: string[]; ips: string[]; urls: string[] };
  created_at: string;
  related_emails: Array<{ id: string; subject: string; from_addr: string }>;
}

export interface EvidenceItem {
  id: string; filename: string; sha256: string; size_bytes: number;
  acquisition_method: string; analyst: string; integrity_status: string;
  case_id: string | null; created_at: string;
}

export const api = {
  dashboard: () => apiGet<DashboardSummary>("/api/v1/dashboard/summary"),

  listEmails: () => apiGet<EmailSummary[]>("/api/v1/emails"),
  getEmailFull: (id: string) => apiGet<EmailFull>(`/api/v1/emails/${id}/full`),
  uploadEmail: (file: File, caseId?: string) =>
    apiUpload<{ email_id: string; evidence_id: string }>(
      `/api/v1/emails/upload${caseId ? `?case_id=${caseId}` : ""}`, file,
    ),
  analyzeRawEmail: (rawEmail: string, caseId?: string) =>
    apiPost<{ email_id: string; evidence_id: string }>("/api/v1/emails/analyze", { raw_email: rawEmail, case_id: caseId }),

  listCases: () => apiGet<CaseSummary[]>("/api/v1/cases"),
  getCase: (id: string) => apiGet<CaseDetail>(`/api/v1/cases/${id}`),
  createCase: (title: string, severity = "LOW", analyst = "Unassigned", summary = "") =>
    apiPost<{ id: string; case_number: string }>("/api/v1/cases", { title, severity, analyst, summary }),
  updateCase: (id: string, patch: Record<string, unknown>) => apiPatch(`/api/v1/cases/${id}`, patch),
  addCaseNote: (id: string, author: string, text: string) =>
    apiPost(`/api/v1/cases/${id}/notes`, { author, text }),
  linkEmailToCase: (caseId: string, emailId: string) =>
    apiPost(`/api/v1/cases/${caseId}/link-email/${emailId}`),

  listEvidence: () => apiGet<EvidenceItem[]>("/api/v1/evidence"),
  verifyEvidence: (id: string) =>
    apiPost<{ integrity_status: string; recorded_sha256?: string; current_sha256?: string; detail?: string }>(
      `/api/v1/evidence/${id}/verify`,
    ),

  listCampaigns: () => apiGet<Campaign[]>("/api/v1/campaigns"),
  recomputeCampaigns: () => apiPost<{ campaign_count: number }>("/api/v1/campaigns/recompute"),

  generateReport: (caseId: string, emailId?: string) =>
    apiPost<{ id: string; generated_at: string; data: Record<string, unknown> }>(
      `/api/v1/reports/${caseId}${emailId ? `?email_id=${emailId}` : ""}`,
    ),
  getReport: (id: string) => apiGet<{ id: string; case_id: string; email_id: string; generated_at: string; data: Record<string, unknown> }>(`/api/v1/reports/${id}`),

  lookupIp: (ip: string) => apiGet<Record<string, unknown>>(`/api/v1/ip/${encodeURIComponent(ip)}`),
  lookupDomain: (domain: string) => apiGet<Record<string, unknown>>(`/api/v1/domains/${encodeURIComponent(domain)}`),
  listIocs: () => apiGet<Array<{ id: string; email_id: string; type: string; value: string; risk: string; confidence: number; source: string }>>("/api/v1/iocs"),
  getSettings: () => apiGet<{ intel_mode: string; app_name: string }>("/api/v1/settings"),
};
