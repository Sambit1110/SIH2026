-- Trace-X production schema for Supabase Postgres.
--
-- This file is the authoritative schema for production. The FastAPI backend
-- does NOT run auto-migration (Base.metadata.create_all) against Postgres --
-- see app/main.py -- specifically so this reviewed, RLS-protected schema is
-- never silently overridden by ORM-inferred DDL.
--
-- Apply via the Supabase SQL editor (paste this whole file and run it), or
-- via the Supabase CLI: `supabase db push`.
--
-- Primary keys are short opaque text ids (12 hex chars, generated in the
-- application as uuid4().hex[:12]) rather than Postgres-native UUIDs --
-- kept as-is from the working SQLite-era schema per "reuse working
-- functionality, refactor only where required." They are TEXT, not
-- auto-incrementing, so this is a purely cosmetic difference from a native
-- UUID column.

-- ============================================================
-- CASES
-- ============================================================
create table if not exists cases (
    id              text primary key,
    case_number     text unique,
    title           text not null,
    status          text not null default 'Open',       -- Open, Investigating, Contained, Resolved, Archived
    severity        text not null default 'LOW',
    analyst         text not null default 'Unassigned',
    summary         text not null default '',
    notes           jsonb not null default '[]',         -- [{author, text, created_at}]
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);
create index if not exists ix_cases_case_number on cases (case_number);
create index if not exists ix_cases_status on cases (status);

-- ============================================================
-- EVIDENCE
-- ============================================================
create table if not exists evidence (
    id                  text primary key,
    case_id             text references cases(id),
    filename            text not null,
    sha256              text not null,
    stored_path         text not null,                   -- storage key: local path (dev) or Supabase Storage object key (prod)
    storage_provider    text not null default 'local',    -- 'local' | 'supabase'
    size_bytes          integer not null default 0,
    acquisition_method  text not null default 'Web Upload',
    analyst             text not null default 'System',
    integrity_status    text not null default 'VERIFIED', -- VERIFIED | TAMPERED | MISSING
    created_at          timestamptz not null default now()
);
create index if not exists ix_evidence_case_id on evidence (case_id);

-- ============================================================
-- EMAILS
-- ============================================================
create table if not exists emails (
    id              text primary key,
    case_id         text references cases(id),
    evidence_id     text references evidence(id),

    from_addr       text,
    to_addr         text,
    cc_addr         text,
    reply_to        text,
    return_path     text,
    subject         text,
    date_header     text,
    message_id      text,

    raw_headers     jsonb not null default '[]',          -- [{name, value}]
    body_text       text not null default '',
    body_html       text not null default '',
    attachments     jsonb not null default '[]',           -- [{filename, size, mime, sha256}]

    demo_case_key   text,
    label           text not null default 'Uploaded',      -- 'Demo' | 'Uploaded'
    created_at      timestamptz not null default now()
);
create index if not exists ix_emails_case_id on emails (case_id);
create index if not exists ix_emails_evidence_id on emails (evidence_id);
create index if not exists ix_emails_created_at on emails (created_at);

-- ============================================================
-- ANALYSIS RESULTS (one-to-one with emails)
-- ============================================================
create table if not exists analysis_results (
    id                      text primary key,
    email_id                text not null unique references emails(id),
    overall_score           double precision,
    severity                text,
    classification          text,
    confidence              double precision,
    sub_scores              jsonb,                          -- {content, sender, authentication, url, infrastructure, impersonation}
    factors                 jsonb,                          -- [{label, points, category, reason}]
    header_findings         jsonb,                          -- [{issue, severity, detail}]
    lookalike_findings      jsonb,                          -- [{observed_domain, target_brand, similarity, reason, confidence}]
    attribution             jsonb,                          -- {conclusion, confidence, evidence_strength, supporting_indicators, limitations}
    created_at              timestamptz not null default now()
);
create index if not exists ix_analysis_results_severity on analysis_results (severity);

-- ============================================================
-- AUTH RESULTS (SPF/DKIM/DMARC, one-to-one with emails)
-- ============================================================
create table if not exists auth_results (
    id                text primary key,
    email_id          text not null unique references emails(id),
    spf               text not null default 'NONE',
    dkim              text not null default 'NONE',
    dmarc             text not null default 'NONE',
    alignment         jsonb not null default '{}',
    source            text not null default 'Reported by Receiving Mail Server',
    raw_auth_header   text not null default ''
);

-- ============================================================
-- IOCS
-- ============================================================
create table if not exists iocs (
    id          text primary key,
    email_id    text references emails(id),
    type        text,                                     -- ip, domain, url, email, hash, message_id, mx
    value       text,
    risk        text not null default 'LOW',
    confidence  double precision not null default 0.5,
    source      text not null default 'Header/Body Extraction',
    extra       jsonb not null default '{}'
);
create index if not exists ix_iocs_email_id on iocs (email_id);
create index if not exists ix_iocs_type on iocs (type);
create index if not exists ix_iocs_value on iocs (value);

-- ============================================================
-- DOMAIN INTEL (cache, keyed by domain)
-- ============================================================
create table if not exists domain_intel (
    id              text primary key,
    domain          text unique,
    registrar       text,
    created_date    text,
    nameservers     jsonb not null default '[]',
    mx              jsonb not null default '[]',
    spf_record      text not null default '',
    reputation      text not null default 'UNKNOWN',
    source          text not null default 'Demo Intelligence Dataset'
);
create index if not exists ix_domain_intel_domain on domain_intel (domain);

-- ============================================================
-- IP INTEL (cache, keyed by ip)
-- ============================================================
create table if not exists ip_intel (
    id              text primary key,
    ip              text unique,
    country         text,
    region          text,
    city            text,
    lat             double precision,
    lon             double precision,
    isp             text,
    asn             text,
    org             text,
    network_type    text not null default 'UNKNOWN',
    reputation      text not null default 'UNKNOWN',
    proxy_vpn_tor   text not null default 'UNKNOWN',
    source          text not null default 'Demo Intelligence Dataset'
);
create index if not exists ix_ip_intel_ip on ip_intel (ip);

-- ============================================================
-- RELAY HOPS
-- ============================================================
create table if not exists relay_hops (
    id                      text primary key,
    email_id                text references emails(id),
    sequence                integer,
    hostname                text,
    ip                      text,
    timestamp               text,
    org                     text,
    confidence              text not null default 'MEDIUM',
    evidence_source         text not null default 'Received Header',
    flags                   jsonb not null default '[]',
    is_earliest_reliable    integer not null default 0
);
create index if not exists ix_relay_hops_email_id on relay_hops (email_id);

-- ============================================================
-- CAMPAIGNS
-- ============================================================
create table if not exists campaigns (
    id                  text primary key,
    campaign_number     text unique,
    name                text,
    technique           text,
    confidence          double precision,
    shared_indicators   jsonb not null default '{}',       -- {domains: [], ips: [], urls: []}
    created_at          timestamptz not null default now()
);

create table if not exists campaign_emails (
    id              text primary key,
    campaign_id     text references campaigns(id),
    email_id        text references emails(id)
);
create index if not exists ix_campaign_emails_campaign_id on campaign_emails (campaign_id);
create index if not exists ix_campaign_emails_email_id on campaign_emails (email_id);

-- ============================================================
-- TIMELINE EVENTS
-- ============================================================
create table if not exists timeline_events (
    id              text primary key,
    case_id         text references cases(id),
    email_id        text references emails(id),
    event_type      text,
    description     text,
    occurred_at     timestamptz not null default now()
);
create index if not exists ix_timeline_events_case_id on timeline_events (case_id);
create index if not exists ix_timeline_events_email_id on timeline_events (email_id);

-- ============================================================
-- REPORTS
-- ============================================================
create table if not exists reports (
    id              text primary key,
    case_id         text references cases(id),
    email_id        text references emails(id),
    generated_at    timestamptz not null default now(),
    data            jsonb
);
create index if not exists ix_reports_case_id on reports (case_id);
create index if not exists ix_reports_email_id on reports (email_id);

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
-- Trace-X's browser client never talks to Supabase directly -- every request
-- goes through the FastAPI backend, which connects with a direct Postgres
-- connection string (DATABASE_URL) that authenticates as a normal Postgres
-- role, not through Supabase's PostgREST/anon-key HTTP layer. That
-- connection is unaffected by RLS.
--
-- RLS is enabled here anyway, as defense-in-depth: Supabase auto-exposes
-- every table through its REST API by default, so if the project's anon or
-- authenticated key were ever leaked or reused elsewhere, RLS with no
-- permissive policies means that key still cannot read or write a single
-- row of investigation/evidence data. This is Supabase's own recommended
-- default posture for any table that shouldn't be browser-readable.
alter table cases              enable row level security;
alter table evidence           enable row level security;
alter table emails             enable row level security;
alter table analysis_results   enable row level security;
alter table auth_results       enable row level security;
alter table iocs               enable row level security;
alter table domain_intel       enable row level security;
alter table ip_intel           enable row level security;
alter table relay_hops         enable row level security;
alter table campaigns          enable row level security;
alter table campaign_emails    enable row level security;
alter table timeline_events    enable row level security;
alter table reports            enable row level security;

-- No policies are created for the anon/authenticated roles: this is
-- intentional and means the PostgREST API (Supabase's browser-facing REST
-- layer, driven by SUPABASE_ANON_KEY) has zero access to any of these
-- tables. The `postgres` role used by DATABASE_URL (and any role with
-- BYPASSRLS, including Supabase's service_role) is unaffected by RLS and
-- retains full access, which is exactly what the FastAPI backend needs and
-- all it needs.
