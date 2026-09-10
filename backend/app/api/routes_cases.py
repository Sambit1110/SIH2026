from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.api.deps import get_db
from app.schemas import CaseCreate, CaseUpdate, NoteCreate

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])

VALID_STATUSES = {"Open", "Investigating", "Contained", "Resolved", "Archived"}


def _next_case_number(db: Session) -> str:
    count = db.query(models.Case).count()
    year = datetime.now(timezone.utc).year
    return f"TX-{year}-{count + 1:03d}"


@router.get("")
def list_cases(db: Session = Depends(get_db)):
    cases = db.query(models.Case).order_by(models.Case.created_at.desc()).all()
    return [
        {
            "id": c.id, "case_number": c.case_number, "title": c.title, "status": c.status,
            "severity": c.severity, "analyst": c.analyst, "created_at": c.created_at,
            "updated_at": c.updated_at, "email_count": len(c.emails), "evidence_count": len(c.evidence),
        }
        for c in cases
    ]


@router.post("")
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    case = models.Case(
        case_number=_next_case_number(db), title=payload.title, severity=payload.severity,
        analyst=payload.analyst, summary=payload.summary, status="Open",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    db.add(models.TimelineEvent(case_id=case.id, event_type="CASE_CREATED", description=f"Case {case.case_number} created."))
    db.commit()
    return {"id": case.id, "case_number": case.case_number}


def _case_or_404(db: Session, case_id: str) -> models.Case:
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case


@router.get("/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db)):
    case = _case_or_404(db, case_id)
    emails = db.query(models.Email).filter(models.Email.case_id == case_id).all()
    evidence = db.query(models.Evidence).filter(models.Evidence.case_id == case_id).all()
    timeline = (
        db.query(models.TimelineEvent)
        .filter(models.TimelineEvent.case_id == case_id)
        .order_by(models.TimelineEvent.occurred_at)
        .all()
    )
    all_iocs = []
    for e in emails:
        all_iocs.extend(db.query(models.IOC).filter(models.IOC.email_id == e.id).all())

    return {
        "id": case.id, "case_number": case.case_number, "title": case.title, "status": case.status,
        "severity": case.severity, "analyst": case.analyst, "summary": case.summary, "notes": case.notes,
        "created_at": case.created_at, "updated_at": case.updated_at,
        "emails": [
            {"id": e.id, "subject": e.subject, "from_addr": e.from_addr,
             "overall_score": e.analysis.overall_score if e.analysis else None,
             "severity": e.analysis.severity if e.analysis else None,
             "classification": e.analysis.classification if e.analysis else None}
            for e in emails
        ],
        "evidence": [
            {"id": ev.id, "filename": ev.filename, "sha256": ev.sha256,
             "integrity_status": ev.integrity_status, "created_at": ev.created_at}
            for ev in evidence
        ],
        "iocs": [{"type": i.type, "value": i.value, "risk": i.risk} for i in all_iocs],
        "timeline": [
            {"event_type": t.event_type, "description": t.description, "occurred_at": t.occurred_at}
            for t in timeline
        ],
    }


@router.patch("/{case_id}")
def update_case(case_id: str, payload: CaseUpdate, db: Session = Depends(get_db)):
    case = _case_or_404(db, case_id)
    if payload.status and payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {sorted(VALID_STATUSES)}")

    changes = []
    for field in ("title", "status", "severity", "analyst", "summary"):
        value = getattr(payload, field)
        if value is not None and value != getattr(case, field):
            changes.append(f"{field}: '{getattr(case, field)}' -> '{value}'")
            setattr(case, field, value)

    db.commit()
    if changes:
        db.add(models.TimelineEvent(case_id=case.id, event_type="CASE_UPDATED", description="; ".join(changes)))
        db.commit()
    return {"ok": True}


@router.post("/{case_id}/notes")
def add_note(case_id: str, payload: NoteCreate, db: Session = Depends(get_db)):
    case = _case_or_404(db, case_id)
    notes = list(case.notes or [])
    notes.append({"author": payload.author, "text": payload.text, "created_at": datetime.now(timezone.utc).isoformat()})
    case.notes = notes
    db.commit()
    return {"ok": True}


@router.post("/{case_id}/link-email/{email_id}")
def link_email(case_id: str, email_id: str, db: Session = Depends(get_db)):
    case = _case_or_404(db, case_id)
    email = db.query(models.Email).filter(models.Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found.")
    email.case_id = case_id
    if email.evidence_record:
        email.evidence_record.case_id = case_id
    db.add(models.TimelineEvent(case_id=case_id, email_id=email_id, event_type="CASE_LINKED",
                                 description=f"Email '{email.subject}' linked to case {case.case_number}."))
    db.commit()
    return {"ok": True}
