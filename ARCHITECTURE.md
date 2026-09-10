# Trace-X Architecture

## System Overview

```
Browser (Next.js)
     │  REST/JSON, TanStack Query
     ▼
FastAPI Application (ASGI)
  ├─ api/            routers per domain (emails, cases, evidence, campaigns, reports, dashboard, intel)
  ├─ core/parsing/    MIME/header parsing, IOC extraction
  ├─ core/forensics/  header-anomaly detection, relay-chain reconstruction, SPF/DKIM/DMARC
  ├─ core/detection/  rule-based threat classifier, lookalike-domain detector, URL risk analyzer
  ├─ core/scoring/    six-signal explainable risk engine
  ├─ core/intel/      GeoIPProvider / DomainIntelProvider (Demo + Live implementations)
  ├─ core/storage/    EvidenceStorageProvider (Local + Supabase implementations)
  ├─ core/graph/      per-email relationship graph builder (→ React Flow JSON)
  ├─ core/campaigns/  deterministic connected-components correlation
  ├─ core/reporting/  aggregates everything into the 19-section forensic report
  └─ core/pipeline.py orchestrates all of the above for one analyzed email
     │
     ▼
SQLAlchemy 2.0  ──►  SQLite (local file) or Supabase PostgreSQL, by DATABASE_URL
EvidenceStorageProvider  ──►  local filesystem or Supabase Storage, by SUPABASE_* env vars
```

One frontend app, one backend app, driven entirely by environment variables to pick their local or
production backing services. This is deliberate: a judge-day demo failure from infrastructure
complexity is a worse outcome than any elegance gained from services that don't need splitting at
this scale, and it means the identical codebase runs unmodified in both environments.

## Development vs Production Architecture

**Local development:**

```
next dev  ──HTTP──►  uvicorn (FastAPI)  ──►  SQLite file  +  local evidence_store/ directory
```

**Production:**

```
GitHub repo
   │
   ├──► Vercel project "frontend" (root: frontend/)  ──►  Next.js, static + SSR
   │        NEXT_PUBLIC_API_URL points at the backend project's URL
   │
   └──► Vercel project "backend"  (root: backend/)   ──►  Python serverless function (FastAPI ASGI)
            DATABASE_URL, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
                 │                           │
                 ▼                           ▼
        Supabase PostgreSQL          Supabase Storage (private "evidence" bucket)
```

Both are deployed **from the same GitHub repository** as two separate Vercel projects with
different "Root Directory" settings — a standard, well-documented Vercel monorepo pattern. See
[Vercel Deployment Architecture](#vercel-deployment-architecture) below for why two projects
rather than co-hosting the Python function inside the Next.js app, and
[DEPLOYMENT.md](DEPLOYMENT.md) for the exact setup steps.

No code branches on which environment it's in. Three things make this work automatically:

1. `app/db.py` builds a SQLite engine when `DATABASE_URL` starts with `sqlite`, and a Postgres
   engine (with `sslmode=require` and a serverless-appropriate `NullPool`) otherwise.
2. `app/core/storage/providers.py`'s `get_evidence_storage()` returns `SupabaseStorageProvider`
   when `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` are set, else `LocalStorageProvider`.
3. `app/main.py` only runs `Base.metadata.create_all()` and auto-seeding against SQLite — Postgres
   schema is owned by the reviewed SQL migration, and Postgres seeding is a deliberate one-time
   command (see below), not something that runs on every serverless cold start.

## Why Supabase PostgreSQL, not SQLite, in Production

SQLite is a single on-disk file. Vercel serverless functions have a read-only deployment
filesystem (only `/tmp` is writable, and it's wiped between invocations) — there is no durable
place for a SQLite file to live there, so SQLite was never viable for production regardless of
preference. Supabase PostgreSQL is the natural fit: fully managed, reachable from Vercel's
serverless functions over the network (unlike a local file), and requires no ORM/query changes
from the SQLite version — the same SQLAlchemy models and every existing endpoint work unmodified
against it. SQLite remains the **local development default** specifically because it removes an
entire class of setup friction (no account, no network dependency, no credentials) for a prototype
that still needs to be trivial to run on a judge's laptop.

## Vercel Deployment Architecture

**Decision: the backend deploys as its own Vercel project (Python ASGI serverless function), separate
from the frontend's Vercel project.** Both come from the same GitHub repo.

Why not rewrite the backend in TypeScript as Next.js Route Handlers (the other realistic option)?
Every piece of Trace-X's detection/scoring/forensics logic is already implemented, tested (51
passing tests), and works — a rewrite would mean re-implementing and re-validating MIME parsing,
header forensics, the six-signal scoring engine, lookalike detection, relay-chain reconstruction,
and campaign correlation from scratch in a second language, for no functional gain. That directly
contradicts "reuse working functionality, refactor only where required."

Why not co-host the Python function inside the `frontend/` Next.js project's own `api/` directory
(one Vercel project instead of two)? Next.js's App Router already owns the `app/api/` path
convention for its own route handlers, and reliably nesting an unrelated Python package (`backend/app/`)
inside the frontend project's build context so Vercel's Python builder can find it introduces
avoidable structural ambiguity. Two Vercel projects from one repo — each pointed at its own
already-standard root directory (`frontend/`, `backend/`) — is a common, well-documented pattern
that lets each half deploy through its own proven, zero-surprise build path:

- **`frontend` project** (root: `frontend/`): zero-config Next.js detection, deploys exactly as it
  does today locally.
- **`backend` project** (root: `backend/`): `backend/api/index.py` re-exports the existing FastAPI
  `app` object; `backend/vercel.json` tells Vercel to run it as a Python 3.11 function and routes
  every path to it. No route-by-route serverless-function split was needed — the whole FastAPI app
  (all ~25 endpoints) runs as one ASGI function, since the entire pipeline for one email completes
  in well under a second, nowhere near Vercel's function duration limits.

Serverless-specific adaptations made to the existing FastAPI app (all covered above/below in more
detail): no local disk writes (evidence → Supabase Storage), no `create_all`/auto-seed against
Postgres on cold start (owned by the SQL migration / a one-time seed command instead), and a
`NullPool` Postgres engine (a serverless instance's own connection pool doesn't help — Supabase's
pgbouncer transaction pooler is the actual pooling layer here).

## Supabase Database Architecture

Schema lives in `backend/supabase/migrations/20260910000000_init_schema.sql` — hand-written to
match the SQLAlchemy models exactly, but using Postgres-native types the ORM's generic column types
don't reach for by default:

- **JSONB, not JSON**, for every structured column (case notes, raw headers, risk-score factors,
  attribution, IOC metadata, etc.) — Postgres's native binary JSON representation, indexable and
  more efficient to query than plain `json`. `app/models.py` defines `JSONType` as
  `JSON().with_variant(JSONB(), "postgresql")`, so the exact same model column renders as `JSONB`
  against Supabase and falls back to plain `JSON` against SQLite locally (where `JSONB` doesn't
  exist) — one model definition, correct on both databases.
- **TIMESTAMPTZ, not TIMESTAMP**, for every datetime column (`DateTime(timezone=True)` in the
  models). This is a correctness fix, not just a preference: every timestamp this app produces is
  already UTC-aware (`datetime.now(timezone.utc)`), and without `timezone=True` Postgres would
  silently create `TIMESTAMP WITHOUT TIME ZONE` columns, which would compare and serialize subtly
  incorrectly against the tz-aware Python values actually being stored.
- **Indexes** on every foreign-key-shaped column that the API actually filters or joins on
  (`emails.case_id`, `iocs.email_id`, `iocs.type`, `relay_hops.email_id`, `timeline_events.case_id`,
  etc.), plus the existing unique indexes on `cases.case_number`, `domain_intel.domain`, and
  `ip_intel.ip`.
- **Text primary keys**, not Postgres-native `uuid` columns — kept as-is from the working
  SQLite-era schema (`uuid4().hex[:12]`, generated in the application) per "reuse working
  functionality, refactor only where required." This is a cosmetic difference from a native UUID
  column, not a functional one.

**Row Level Security is enabled on every table, with zero permissive policies.** This deserves
explanation, since Trace-X's browser client never talks to Supabase directly — every request goes
through the FastAPI backend, which connects with `DATABASE_URL` as a normal Postgres role (or the
service role), both of which bypass RLS entirely as far as Postgres is concerned. So why enable it?
Because Supabase auto-exposes **every** table through its PostgREST HTTP API by default, keyed by
the project's anon/authenticated keys — RLS with no policies is what guarantees that even if those
keys were ever reused elsewhere or leaked, they still cannot read or write a single row of
investigation or evidence data. This is Supabase's own recommended default posture, applied here as
defense-in-depth rather than as something this architecture's own data flow strictly requires.

Applying the schema is a one-time, explicit step (paste `20260910000000_init_schema.sql` into the
Supabase SQL editor, or `supabase db push`) — the backend deliberately does **not** run
`Base.metadata.create_all()` against Postgres (see `app/main.py`), so the reviewed migration is
always the single source of truth for the production schema; it can never silently drift from
whatever the ORM would have inferred.

## Evidence Storage Architecture

`app/core/storage/providers.py` defines `EvidenceStorageProvider` with two implementations,
selected automatically by `get_evidence_storage()` based on whether Supabase credentials are
configured:

- **`LocalStorageProvider`** — writes/reads `backend/evidence_store/`. Used whenever
  `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` aren't set, i.e. local development. Never selected in
  production (Vercel's deployed source directory is read-only outside `/tmp`, which isn't durable
  across invocations anyway).
- **`SupabaseStorageProvider`** — uploads/downloads via the Supabase Storage REST API, authenticated
  with `SUPABASE_SERVICE_ROLE_KEY` (a server-side-only secret; see `backend/.env.example`'s
  warnings). The backing bucket (`evidence`, created by
  `backend/supabase/migrations/20260910000001_storage_bucket.sql`) is created **private**
  (`public = false`) — evidence is never reachable by a public URL. Because the service role key
  bypasses Supabase Storage's own RLS/policy layer by design, no bucket policies need to be
  authored for this backend to work; the browser never holds a key capable of reading the bucket at
  all.

Both providers implement the same two-method interface (`upload(filename, content) -> storage_key`,
`download(storage_key) -> bytes | None`), so every caller — the upload endpoint, the raw-email-paste
endpoint, the evidence integrity re-verification endpoint, and the demo seed script — is identical
regardless of which environment it's running in. The seed script uploads the bundled demo `.eml`
files through this same abstraction (rather than pointing directly at the file on disk), so seeded
demo evidence is indistinguishable from real uploaded evidence for every downstream feature,
including hash re-verification.

## Report Generation and Serverless Compatibility

Forensic reports were already serverless-compatible before this migration and needed no change:
`core/reporting/builder.py` assembles a plain JSON structure from data already in the database (no
new analysis, no template rendering, no binary artifact), it's stored as a `JSONB` row in the
`reports` table, and the frontend renders it as a page with a browser "Print / Save as PDF" action.
There is no PDF-generation step, so there's nothing that depends on local disk, a long-running
process, or a system library (e.g. WeasyPrint's Pango/Cairo dependency) that wouldn't survive a
serverless environment.

## One-Time Production Seeding

Demo-case seeding auto-runs on startup **only** against SQLite (see `app/main.py`). Against
Postgres, it's a deliberate, explicit command run once after the schema migration is applied:

```bash
DATABASE_URL="<your Supabase connection string>" python -m app.seed.seed_data
```

This avoids two real problems an always-auto-seed approach would have in serverless: (1) two
concurrent cold starts racing to both seed an empty database simultaneously (low probability, but
a real race condition against a shared external database that SQLite's single-file/single-process
local model never had to worry about), and (2) re-running seed-eligibility checks (`SELECT COUNT(*)
FROM cases`) against Supabase on every cold start for no benefit once already seeded. The check
itself (`if db.query(Case).count() > 0: return`) is unchanged and still idempotent — running the
command again after the database is already seeded is a safe no-op.

## Threat Scoring Methodology

Six independently-computed sub-scores (0–100), each backed by a list of signed point
contributions with a human-readable reason (`app/core/scoring/engine.py`):

- **Content Risk** — phishing/BEC/fraud/social-engineering language, lexicon + regex based
- **Sender Risk** — From/Reply-To/Return-Path mismatches, sender domain reputation, domain age
- **Authentication Risk** — SPF/DKIM/DMARC results
- **URL Risk** — IP-literal URLs, suspicious TLDs, shorteners, encoding
- **Infrastructure Risk** — observed IP reputation, proxy/VPN indicators, relay anomalies
- **Impersonation Risk** — executive-authority language, lookalike-domain findings

**Overall score is the capped SUM of every individual factor's points (scaled by a single
constant), not a weighted average of the six sub-scores.** This was a deliberate design change
during implementation: an average-of-sub-scores model punishes attacks that legitimately don't
touch every vector (a BEC email with no URL at all correctly has URL Risk = 0, but that must not
drag down an otherwise overwhelming set of sender/content/auth signals). Summing keeps the overall
score directly traceable to the visible factor list — "the score is exactly what you see added up
below, capped at 100" — which is a stronger form of explainability than a black-box weighted blend.

Severity thresholds: `≥85 CRITICAL`, `≥65 HIGH`, `≥40 MEDIUM`, else `LOW`. Classification is decided
by checking for specific, actionable technique signals in priority order (not by whichever
technique bucket accumulates the most points) — see the docstring on `_classify()` for why BEC vs.
Vendor Invoice Fraud specifically needs an executive-authority-language tiebreaker, since both
share the same payment-diversion phrase bank.

Everything here is deterministic: no randomness, no LLM call, same input always produces the same
score and the same explanation. The engine is built behind a stable `classify()` function signature
specifically so a trained ML/NLP model can later replace or blend with the heuristic engine without
touching any caller.

## Demo Mode Architecture

`INTEL_MODE=demo` (default) or `live`. Provider factories (`app/core/intel/providers.py`) resolve
to `DemoGeoIPProvider`/`DemoDomainIntelProvider` (deterministic, versioned JSON fixtures under
`app/core/intel/fixtures/`, zero network calls) or their `Live` counterparts, which attempt a real
lookup (ip-api.com for geolocation, RDAP for domain registration) with a 2.5s timeout and
automatically fall back to the demo provider on any failure — the result's `source` field always
reflects what actually happened (`Live Geolocation Provider` vs. `Demo Intelligence Dataset (live
lookup unavailable, fell back automatically)`). Demo data is never silently relabeled as live, and
vice versa.

Six demo cases are seeded idempotently on startup (`app/seed/seed_data.py`) from real `.eml` files
under `app/seed/emails/` — see [DEMO.md](DEMO.md) for what each one demonstrates.

## Campaign Correlation — a bug found and fixed during build

The correlation engine (`app/core/campaigns/correlation.py`) groups emails via connected
components over shared domain/IP/URL indicators. During integration testing, two false positives
surfaced and were fixed:

1. **Private IPs are not correlatable.** Several demo `.eml` files reuse the same internal mail
   gateway IP (`10.10.4.12`) for realism. Treating that as a shared indicator incorrectly grouped
   unrelated emails (including the benign control case) into one "campaign." Fixed by excluding
   `ip`-type IOCs where `ipaddress.ip_address(...).is_private` is true.
2. **Internal relay hostnames are not IOC-worthy.** A relay hop's hostname was extracted as a
   generic `domain` IOC regardless of whether that hop's IP was public or private. This meant the
   *recipient organization's own* mail server hostname (e.g.
   `mailstore-internal.northbridge-financial.com`) got treated as shared attacker infrastructure
   across every email that happened to transit it. Fixed in `app/core/pipeline.py` by only
   including a relay hop's hostname in domain extraction when that hop's IP is public.

Both fixes are covered by `backend/tests/test_campaign_correlation.py` and by re-verifying the
seeded dataset after each fix (see the retro in this file's git history / session log).

## Frontend Architecture

Next.js App Router, one route per nav item. Server components are only used as thin async
wrappers for dynamic routes (`[id]/page.tsx` awaits `params`, then renders a client component) —
everything else is a client component driven by TanStack Query against the FastAPI backend, since
the app is fundamentally an API-driven investigation console, not a content site.

- **React Flow** (`components/graph/GraphView.tsx`) renders the per-email infrastructure graph
  returned by `/api/v1/emails/{id}/graph`, colored by node risk, with a click-to-inspect panel.
- **MapLibre GL** (`components/map/GeoMap.tsx`) plots relay-hop geolocation. It uses MapLibre's own
  `demotiles.maplibre.org` style rather than hitting `tile.openstreetmap.org` raster tiles
  directly — OSM's raw tile server is rate-limited for non-browser/bulk traffic and proved
  unreliable in testing; the demo-tiles style is explicitly provided for this kind of use and
  degrades gracefully (markers still render even if the basemap fails to load).
- **Reports** are rendered as a light "document" card (independent of the app's dark console
  theme) with a `window.print()` "Print / Save as PDF" action and a `.no-print` class on the
  sidebar/topbar — this avoids a system-dependent PDF-rendering library (e.g. WeasyPrint, which
  needs Pango/Cairo installed) as a demo-day failure point.

## Security & Privacy

- Uploads: extension allowlist (`.eml`/`.txt`), 10MB size cap, empty-file rejection
- Attachments are captured as metadata (filename/size/mime/SHA-256) only — never opened or executed
- No server-side fetch of arbitrary URLs found in email bodies (SSRF avoidance) — URL analysis is
  purely string-based
- SQLAlchemy ORM only, no raw SQL string interpolation
- CORS restricted to configured frontend origins — localhost defaults plus whatever's in
  `CORS_ORIGINS_EXTRA` (set to the deployed frontend's Vercel URL in production); never a
  hardcoded production hostname in source
- Evidence integrity: SHA-256 computed at ingestion, re-verifiable on demand
  (`POST /api/v1/evidence/{id}/verify`)
- `SUPABASE_SERVICE_ROLE_KEY` is read only server-side (`app/config.py`, via `pydantic-settings`)
  and is never referenced by any frontend code or `NEXT_PUBLIC_`-prefixed variable — it cannot
  reach the browser
- Row Level Security enabled on every Supabase table and on `storage.objects`, with no
  anon/authenticated policies — see [Supabase Database Architecture](#supabase-database-architecture)

## What Was Deliberately Not Built

Per the original architecture review, and reconfirmed at implementation time:

- No Redis/Celery/message queues — the analysis pipeline runs synchronously in a few hundred
  milliseconds; there's no workload here that benefits from async task queuing
- No Kubernetes/Docker Compose orchestration — two processes (`uvicorn`, `next dev`) is the whole
  deployment
- No authentication/RBAC — single-analyst prototype; noted as a real gap if this became a
  production system, out of scope for a 5-minute SIH demo. **Supabase Auth was deliberately not
  added** during the Supabase migration either: the brief called it explicitly optional ("if
  useful"), and there's no multi-analyst requirement driving it yet. The natural next step, if this
  becomes multi-analyst, is Supabase Auth issuing a JWT the FastAPI backend verifies per-request —
  the RLS policies already in the schema migration would then extend naturally to per-user data
  scoping instead of the current all-or-nothing posture.
- No full DKIM cryptographic re-verification — the platform reports what the receiving MTA already
  computed (`Authentication-Results` header), labeled accordingly
- No live SMTP receiving server — upload/paste based ingestion only
- No TypeScript rewrite of the backend — see
  [Vercel Deployment Architecture](#vercel-deployment-architecture) for why the working, tested
  Python implementation was adapted for serverless rather than reimplemented
