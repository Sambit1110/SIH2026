"""Deterministic demo-mode seed data: 5 synthetic cases covering BEC,
credential phishing, vendor invoice fraud, a legitimate control email, and a
lookalike-domain attack. All content is fictional; no real people's data is
used. Runs once, idempotently, on application startup when the database is
empty, so the platform is immediately demo-ready with zero external calls.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from app import models
from app.core.campaigns.correlation import recompute_campaigns
from app.core.parsing.email_parser import parse_eml_bytes
from app.core.pipeline import analyze_email
from app.core.storage.providers import get_evidence_storage
from app.db import SessionLocal, build_session_local

EMAILS_DIR = Path(__file__).parent / "emails"

DEMO_CASES = [
    {
        "key": "case-01",
        "file": "case_01_bec.eml",
        "title": "Suspected CEO Impersonation / Wire Transfer Fraud",
        "status": "Investigating",
        "analyst": "A. Sharma",
        "summary": "Executive impersonation email requesting an urgent, confidential wire transfer to a "
                    "newly introduced beneficiary account. Sender domain is a close typo of the real "
                    "corporate domain.",
        "base_time": datetime(2026, 9, 8, 9, 14, 22, tzinfo=timezone.utc),
    },
    {
        "key": "case-02",
        "file": "case_02_phishing.eml",
        "title": "Microsoft 365 Credential Phishing Campaign",
        "status": "Contained",
        "analyst": "R. Iyer",
        "summary": "Fake Microsoft account-suspension alert directing recipients to a credential-harvesting "
                    "page on a newly registered lookalike domain.",
        "base_time": datetime(2026, 9, 9, 14, 2, 11, tzinfo=timezone.utc),
    },
    {
        "key": "case-03",
        "file": "case_03_invoice_fraud.eml",
        "title": "Vendor Invoice / Payment Diversion Attempt",
        "status": "Open",
        "analyst": "Unassigned",
        "summary": "Vendor-impersonation email requesting a change of banking details for an outstanding "
                    "invoice, sent from a Reply-To domain that does not match the claimed vendor.",
        "base_time": datetime(2026, 9, 10, 11, 20, 52, tzinfo=timezone.utc),
    },
    {
        "key": "case-04",
        "file": "case_04_legitimate.eml",
        "title": "Routine Institutional Notification (Benign)",
        "status": "Resolved",
        "analyst": "A. Sharma",
        "summary": "Legitimate semester-registration confirmation from a verified institutional domain. "
                    "Retained as a baseline/control case; no malicious indicators identified.",
        "base_time": datetime(2026, 9, 11, 8, 5, 38, tzinfo=timezone.utc),
    },
    {
        "key": "case-05",
        "file": "case_05_lookalike.eml",
        "title": "PayPal Brand Impersonation / Lookalike Domain",
        "status": "Open",
        "analyst": "R. Iyer",
        "summary": "Account-limitation phishing lure sent from a homoglyph lookalike of paypal.com, "
                    "hosted on infrastructure with anonymizing network characteristics.",
        "base_time": datetime(2026, 9, 12, 19, 44, 10, tzinfo=timezone.utc),
    },
    {
        "key": "case-06",
        "file": "case_06_phishing_wave2.eml",
        "title": "Microsoft 365 Credential Phishing - Second Wave",
        "status": "Open",
        "analyst": "R. Iyer",
        "summary": "A second, differently-worded phishing email sent from the same malicious domain and "
                    "hosting infrastructure as the earlier Microsoft 365 phishing campaign -- correlated "
                    "automatically as part of the same campaign.",
        "base_time": datetime(2026, 9, 9, 21, 39, 58, tzinfo=timezone.utc),
    },
]


def run_seed_if_empty(session_factory=SessionLocal) -> None:
    db = session_factory()
    try:
        if db.query(models.Case).count() > 0:
            return

        # Goes through the same EvidenceStorageProvider a real upload would
        # (Supabase Storage in production, local filesystem in dev) rather
        # than pointing straight at the bundled .eml source file -- keeps
        # seeded demo evidence indistinguishable from real evidence for
        # integrity re-verification, and works even though the deployed
        # source tree isn't a directory the app can casually declare
        # "evidence lives in this file" against.
        storage = get_evidence_storage()

        for entry in DEMO_CASES:
            raw = (EMAILS_DIR / entry["file"]).read_bytes()

            case = models.Case(
                case_number=f"TX-2026-{len(db.query(models.Case).all()) + 1:03d}",
                title=entry["title"],
                status=entry["status"],
                severity="LOW",
                analyst=entry["analyst"],
                summary=entry["summary"],
                created_at=entry["base_time"],
                updated_at=entry["base_time"],
            )
            db.add(case)
            db.flush()

            evidence = models.Evidence(
                case_id=case.id,
                filename=entry["file"],
                sha256=hashlib.sha256(raw).hexdigest(),
                stored_path=storage.upload(entry["file"], raw),
                storage_provider=storage.name,
                size_bytes=len(raw),
                acquisition_method="Seeded Demo Dataset",
                analyst="System",
                integrity_status="VERIFIED",
                created_at=entry["base_time"],
            )
            db.add(evidence)
            db.flush()

            db.add(models.TimelineEvent(
                case_id=case.id, event_type="CASE_CREATED",
                description=f"Case {case.case_number} created from seeded demo dataset.",
                occurred_at=entry["base_time"],
            ))

            parsed = parse_eml_bytes(raw)
            email = analyze_email(
                db, parsed,
                case_id=case.id, evidence_id=evidence.id,
                demo_case_key=entry["key"], label="Demo",
                base_time=entry["base_time"],
            )
            if email.analysis:
                case.severity = email.analysis.severity
            # No per-case commit here (deliberately) -- see the
            # use_null_pool=False session this function is called with for
            # the __main__ / production-seeding path below. One commit for
            # the whole run means one connection for the whole run instead
            # of a fresh one per case, and as a side benefit makes seeding
            # all-or-nothing: a failure partway through leaves nothing
            # committed, rather than a partially-seeded case list.

        recompute_campaigns(db)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    # One-time production seeding: run this once against the Supabase
    # DATABASE_URL after applying backend/supabase/migrations/0001_init_schema.sql
    # (documented in DEPLOYMENT.md), e.g.:
    #
    #   DATABASE_URL="postgresql://...supabase.co:5432/postgres?sslmode=require" \
    #       python -m app.seed.seed_data
    #
    # Deliberately a manual, explicit step rather than something that runs
    # automatically on every serverless cold start -- see app/main.py.
    from app.config import settings

    print(f"Seeding {settings.database_url.split('@')[-1] if '@' in settings.database_url else settings.database_url} ...")
    # use_null_pool=False: reuse one physical connection for this script's
    # entire run instead of opening a fresh one on every commit (the
    # shared app.db.SessionLocal/NullPool combination is correct for the
    # live serverless API -- see db.py -- but wrong for a script that
    # issues several sequential commits in one process; repeatedly
    # reconnecting to Supabase's Session Pooler in quick succession is what
    # caused this script's intermittent EAUTHTIMEOUT failure).
    run_seed_if_empty(session_factory=build_session_local(use_null_pool=False))
    print("Done. (No-op if the database already had cases.)")
