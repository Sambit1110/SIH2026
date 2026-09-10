# Trace-X

**AI-Powered Email Threat Detection, GeoLocation and Forensic Intelligence Platform**

SIH 2026 prototype. Trace-X ingests a raw email, parses and forensically analyzes its headers,
authentication, and content, extracts indicators of compromise, enriches them with IP/domain
intelligence, reconstructs the relay path and maps observed infrastructure, correlates related
emails into campaigns, and generates a structured forensic report — one integrated investigation,
not a set of disconnected tools.

**DETECT → TRACE → CORRELATE → INVESTIGATE → REPORT**

## Live Demo

**[https://sih-2026-b67y.vercel.app](https://sih-2026-b67y.vercel.app)** — the deployed production
demo. Open it directly in a browser; no setup, no account, and no API keys are required (Demo Mode
is on by default). See [DEMO.md](DEMO.md) for the guided judge walkthrough.

| | |
|---|---|
| **Live Demo** (primary) | **[sih-2026-b67y.vercel.app](https://sih-2026-b67y.vercel.app)** |
| Backend API | [sih-2026-red.vercel.app](https://sih-2026-red.vercel.app) |
| API Health | [sih-2026-red.vercel.app/api/v1/health](https://sih-2026-red.vercel.app/api/v1/health) |

See [ARCHITECTURE.md](ARCHITECTURE.md) for design details, [API.md](API.md) for the endpoint
reference, [DEMO.md](DEMO.md) for the judge demonstration script, and
[DEPLOYMENT.md](DEPLOYMENT.md) for the Supabase + Vercel production deployment walkthrough.

## Two architectures, one codebase

Trace-X runs in two modes from the exact same code:

| | Local development | Production |
|---|---|---|
| Database | SQLite (zero setup) | Supabase PostgreSQL |
| Evidence storage | Local filesystem | Supabase Storage (private bucket) |
| Frontend host | `next dev` | Vercel |
| Backend host | `uvicorn` | Vercel (Python serverless function) |

No code branches on "am I local or in prod" — the same `DATABASE_URL`-driven SQLAlchemy layer and
the same `EvidenceStorageProvider` abstraction pick the right backend automatically based on which
environment variables are set. See [ARCHITECTURE.md](ARCHITECTURE.md#development-vs-production-architecture)
for the full picture.

## Stack

- **Frontend**: Next.js 16 (App Router) + TypeScript + Tailwind CSS + shadcn/ui-style components +
  Framer Motion + React Flow + MapLibre GL + TanStack Query — deployed to **Vercel**
- **Backend**: Python 3.11 + FastAPI + SQLAlchemy 2.0 — deployed to **Vercel** as a Python
  serverless function (ASGI)
- **Database**: SQLite locally (zero setup) / **Supabase PostgreSQL** in production — same
  SQLAlchemy models, driven entirely by `DATABASE_URL`
- **Evidence storage**: local filesystem locally / **Supabase Storage** (private bucket) in
  production, behind an `EvidenceStorageProvider` abstraction
- **Intelligence**: pluggable provider interfaces (`GeoIPProvider`, `DomainIntelProvider`), each
  with a deterministic `Demo` implementation (default, zero network calls) and a `Live`
  implementation (RDAP / DNS / ip-api.com) that automatically falls back to demo data on any
  failure — see [ARCHITECTURE.md](ARCHITECTURE.md#demo-mode-architecture)

No Docker, Redis, Celery, Kubernetes, or other infrastructure is required to run, demo, or deploy
this project.

## Prerequisites

- Python 3.11+ (3.9 will NOT work — the codebase uses `X | None` union syntax throughout)
- Node.js 20+
- No external API keys required for local development or for Demo Mode in production (Demo Mode
  is the default and needs none)
- For production only: a free [Supabase](https://supabase.com) project and a
  [Vercel](https://vercel.com) account — see [DEPLOYMENT.md](DEPLOYMENT.md)

## Local Setup & Run

### Backend

```bash
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional — defaults already work (SQLite, Demo Mode)
uvicorn app.main:app --reload --port 8000
```

On first startup, the backend automatically seeds the local SQLite database with 6 deterministic
demo cases (see [DEMO.md](DEMO.md)) if it's empty. The API is now live at `http://localhost:8000`
(interactive docs at `http://localhost:8000/docs`).

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # optional — defaults already point at localhost:8000
npm run dev
```

Open `http://localhost:3000` (or whichever port Next.js prints, if 3000 is already in use).

## Environment Variables

**Backend** (`backend/.env`, all optional for local dev — see `backend/.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./trace_x.db` | SQLAlchemy connection string. **Required in production** — a Supabase Postgres connection string (pooler, port 6543 recommended). |
| `INTEL_MODE` | `demo` | `demo` (default, no network calls) or `live` (attempts real IP/domain lookups, auto-falls-back to demo on failure). |
| `SUPABASE_URL` | _(unset)_ | Supabase project URL. **Required in production** — enables Supabase Storage for evidence. |
| `SUPABASE_ANON_KEY` | _(unset)_ | Public Supabase key. Accepted for documentation completeness; unused server-side today. |
| `SUPABASE_SERVICE_ROLE_KEY` | _(unset)_ | **Server-side secret.** **Required in production.** Never expose to any client. |
| `SUPABASE_STORAGE_BUCKET` | `evidence` | Private Storage bucket name for evidence files. |
| `CORS_ORIGINS_EXTRA` | _(unset)_ | Comma-separated extra allowed frontend origins (e.g. the deployed frontend's Vercel URL), appended to the localhost defaults. |

**Frontend** (`frontend/.env.local`):

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Base URL of the backend API. In production, set to the deployed backend Vercel project's URL. |

## Testing

```bash
# Backend — 51 tests covering parsing, forensics, scoring, detection, campaigns, storage, and the full API flow
cd backend && source venv/bin/activate && pytest -v

# Frontend — type-check, lint, and production build
cd frontend && npx tsc --noEmit && npm run lint && npm run build
```

## Demo Mode

The platform is demo-ready out of the box, locally and in production: 6 synthetic cases (BEC,
credential phishing x2 as a correlated campaign, vendor invoice fraud, a legitimate control email,
and a lookalike-domain attack) are seeded (automatically for local SQLite; via one explicit command
for production Supabase — see [DEPLOYMENT.md](DEPLOYMENT.md)). All intelligence data is clearly
labeled `Demo Intelligence Dataset` or `Reported by Receiving Mail Server` — nothing fake is ever
presented as live. See [DEMO.md](DEMO.md) for the exact judge walkthrough.

## Repository Layout

```
backend/    FastAPI application, detection/scoring engines, tests, seed data
            backend/api/index.py       Vercel serverless entrypoint
            backend/vercel.json        Vercel Python function config
            backend/supabase/          SQL migrations (schema + storage bucket)
frontend/   Next.js application (SOC/DFIR-styled investigation UI)
```

## Deploying to Production

See [DEPLOYMENT.md](DEPLOYMENT.md) for the full Supabase + Vercel walkthrough. In short: create a
Supabase project, run the two SQL migrations in `backend/supabase/migrations/`, deploy `backend/`
and `frontend/` as two separate Vercel projects from this one GitHub repo, wire the environment
variables between them, and run the seed script once.

## Responsible Attribution

Trace-X deliberately avoids overclaiming. IP geolocation and infrastructure correlation describe
**observed technical infrastructure** — hosting provider, ASN, approximate location — never the
physical identity or exact location of a person. Every attribution assessment in the UI and in
generated reports states this explicitly and separates observation, evidence, inference, and
attribution.
