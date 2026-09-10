from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_campaigns,
    routes_cases,
    routes_dashboard,
    routes_emails,
    routes_evidence,
    routes_intel,
    routes_reports,
)
from app.config import settings
from app.db import Base, engine
from app.seed.seed_data import run_seed_if_empty

if not settings.is_postgres:
    # SQLite (local dev) only: create_all is a convenient, idempotent
    # auto-migration for a throwaway local file. Production Postgres schema
    # is owned by backend/supabase/migrations/0001_init_schema.sql, applied
    # once via the Supabase SQL editor or `supabase db push` -- running
    # create_all against it on every cold start would let the ORM's implicit
    # schema silently diverge from the reviewed, RLS-protected migration.
    Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.is_postgres:
        # Same reasoning as above: in production, seeding is a deliberate,
        # one-time step (`python -m app.seed.seed_data` against the Supabase
        # DATABASE_URL, documented in DEPLOYMENT.md) rather than something
        # that runs implicitly on every cold start -- avoids two concurrent
        # cold starts racing to seed the same empty database.
        run_seed_if_empty()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_emails.router)
app.include_router(routes_cases.router)
app.include_router(routes_evidence.router)
app.include_router(routes_campaigns.router)
app.include_router(routes_reports.router)
app.include_router(routes_dashboard.router)
app.include_router(routes_intel.router)


@app.get("/")
def root():
    return {"app": settings.app_name, "status": "running", "intel_mode": settings.intel_mode}


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}
