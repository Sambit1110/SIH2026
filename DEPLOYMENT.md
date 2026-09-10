# Deploying Trace-X: GitHub → Vercel → Supabase

This walks through taking Trace-X from this repository to a live production deployment at
`https://<your-frontend-project>.vercel.app`, backed by Supabase PostgreSQL and Supabase Storage.

Two Vercel projects are created from this one GitHub repo — see
[ARCHITECTURE.md](ARCHITECTURE.md#vercel-deployment-architecture) for why.

## 1. Create a Supabase project

1. Go to [supabase.com](https://supabase.com) → New Project.
2. Choose a name, database password (save it), and region.
3. Wait for provisioning to finish (a couple of minutes).

## 2. Create the database schema

1. In the Supabase dashboard, open **SQL Editor**.
2. Paste the full contents of
   [`backend/supabase/migrations/20260910000000_init_schema.sql`](backend/supabase/migrations/20260910000000_init_schema.sql)
   and run it. This creates all 13 tables, their indexes, and enables Row Level Security on each
   (see [ARCHITECTURE.md](ARCHITECTURE.md#supabase-database-architecture) for why RLS is enabled
   with no policies).
3. Paste and run
   [`backend/supabase/migrations/20260910000001_storage_bucket.sql`](backend/supabase/migrations/20260910000001_storage_bucket.sql)
   next — creates the private `evidence` Storage bucket.

(If you prefer the Supabase CLI: `supabase link` then `supabase db push` applies both files from
`backend/supabase/migrations/` in order.)

## 3. Configure Supabase Storage

Step 2 already created the bucket via SQL. Confirm it in the dashboard: **Storage** → you should
see an `evidence` bucket marked **Private**. Nothing else to configure — the backend authenticates
with the service role key, which bypasses Storage policies entirely, so no bucket policies need to
be created.

## 4. Collect your Supabase credentials

From **Project Settings**:

- **Database** → **Connection string** → **Transaction pooler** (port 6543) — this is your
  `DATABASE_URL`. Append `?sslmode=require` if it isn't already present. The transaction pooler
  (not the direct connection) is recommended for serverless functions — see
  [ARCHITECTURE.md](ARCHITECTURE.md#vercel-deployment-architecture).
- **API** → `Project URL` — this is `SUPABASE_URL`.
- **API** → `anon` `public` key — this is `SUPABASE_ANON_KEY` (optional, documented for
  completeness).
- **API** → `service_role` `secret` key — this is `SUPABASE_SERVICE_ROLE_KEY`. **Treat this like a
  root database password. Never put it in frontend code or a `NEXT_PUBLIC_` variable.**

## 5. Push this repository to GitHub

If it isn't already there: create a GitHub repo and push this project to it (both `frontend/` and
`backend/` in one repo, as they are now).

## 6. Create the backend Vercel project

1. In Vercel: **Add New** → **Project** → import your GitHub repo.
2. Set **Root Directory** to `backend`.
3. Framework Preset: Vercel should detect Python automatically from `backend/vercel.json` and
   `backend/api/index.py`. If prompted, choose "Other".
4. Under **Environment Variables**, add:

   | Name | Value |
   |---|---|
   | `DATABASE_URL` | the Supabase Transaction pooler connection string from step 4 |
   | `SUPABASE_URL` | from step 4 |
   | `SUPABASE_SERVICE_ROLE_KEY` | from step 4 |
   | `SUPABASE_STORAGE_BUCKET` | `evidence` |
   | `INTEL_MODE` | `demo` (recommended for the judge demo — zero external dependencies) |
   | `CORS_ORIGINS_EXTRA` | leave blank for now — you'll add the frontend URL after step 7 |

5. Deploy. Note the resulting URL, e.g. `https://trace-x-backend.vercel.app`.

## 7. Create the frontend Vercel project

1. In Vercel: **Add New** → **Project** → import the **same** GitHub repo again.
2. Set **Root Directory** to `frontend`.
3. Framework Preset: Next.js (auto-detected).
4. Under **Environment Variables**, add:

   | Name | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | the backend URL from step 6, e.g. `https://trace-x-backend.vercel.app` |

5. Deploy. Note the resulting URL, e.g. `https://trace-x-frontend.vercel.app`.

## 8. Close the loop: allow the frontend's origin in the backend's CORS

1. Back in the **backend** Vercel project's Environment Variables, set:

   | Name | Value |
   |---|---|
   | `CORS_ORIGINS_EXTRA` | `https://trace-x-frontend.vercel.app` (your actual frontend URL from step 7) |

2. Redeploy the backend project (Vercel → Deployments → ⋯ → Redeploy) so the new env var takes
   effect.

## 9. Seed the demo cases

Run this once, from your local machine, against the production database (requires the backend's
Python environment — see [README.md](README.md#local-setup--run) if not already set up locally):

```bash
cd backend
source venv/bin/activate
DATABASE_URL="<your Supabase Transaction pooler connection string>" python -m app.seed.seed_data
```

This is safe to re-run — it's a no-op once the database already has cases (see
[ARCHITECTURE.md](ARCHITECTURE.md#one-time-production-seeding)).

## 10. Verify the deployment

Work through this checklist against your live URLs:

1. **Backend health**: `curl https://<backend-url>/api/v1/health` → `{"status":"ok"}`
2. **Backend root**: `curl https://<backend-url>/` → `{"app":"Trace-X","status":"running","intel_mode":"demo"}`
3. **Demo Mode verification**: `curl https://<backend-url>/api/v1/dashboard/summary` → should show
   `emails_analyzed: 6`, `campaign_count: 1`, etc. (confirms step 9's seeding worked)
4. **Frontend loads**: open `https://<frontend-url>/overview` in a browser — dashboard should
   populate with the same seeded metrics, with zero console errors
5. **Email analysis end-to-end**: Email Analyzer → open any seeded demo case → walk through every
   tab (Threat Summary, Authentication, Header Forensics, IOCs, Relay Trace, Geolocation,
   Infrastructure Graph, AI Assessment, Original Email) — all should render with real data
6. **Database persistence**: Investigations → open a case → Generate Report → refresh the page →
   confirm the report is still retrievable (proves it round-tripped through Supabase Postgres, not
   an in-memory/ephemeral store)
7. **Evidence storage**: Evidence → click **Re-verify** on any row → should return `VERIFIED`
   (proves the file round-tripped through Supabase Storage, not local disk)
8. **Live upload**: Email Analyzer → paste a raw email → Analyze → confirm it produces a real,
   non-seeded analysis (proves the full pipeline works for new evidence, not just seeded data)

## 11. Optional: live intelligence mode

Demo Mode (`INTEL_MODE=demo`) requires nothing further and is what's recommended for the SIH demo.
If you want to additionally exercise the live-lookup code path (real RDAP/DNS/IP-geolocation
calls, all keyless/free-tier), set `INTEL_MODE=live` on the backend Vercel project and redeploy —
every live lookup still automatically falls back to demo data on any failure, so this can't break
the demo even with a live production key removed or misconfigured.

## 12. Redeploying after code changes

Both Vercel projects auto-deploy on push to the connected branch (default: your repo's default
branch) once set up this way — no manual redeploy step needed for ordinary code changes. Database
schema changes require re-running the relevant SQL migration file in the Supabase SQL editor (or
`supabase db push`) — they are not applied automatically by the app in production, by design (see
[ARCHITECTURE.md](ARCHITECTURE.md#supabase-database-architecture)).
