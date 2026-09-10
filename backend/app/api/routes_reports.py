from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.api.deps import get_db
from app.core.reporting.builder import build_report

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.post("/{case_id}")
def generate_report(case_id: str, email_id: str | None = None, db: Session = Depends(get_db)):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found.")

    email = None
    if email_id:
        email = db.query(models.Email).filter(models.Email.id == email_id, models.Email.case_id == case_id).first()
    else:
        email = db.query(models.Email).filter(models.Email.case_id == case_id).order_by(models.Email.created_at.desc()).first()

    if not email:
        raise HTTPException(status_code=400, detail="Case has no analyzed email to report on.")

    data = build_report(db, case, email)
    report = models.Report(case_id=case_id, email_id=email.id, data=data)
    db.add(report)
    db.add(models.TimelineEvent(case_id=case_id, email_id=email.id, event_type="REPORT_GENERATED",
                                 description="Forensic report generated."))
    db.commit()
    db.refresh(report)
    return {"id": report.id, "generated_at": report.generated_at, "data": report.data}


@router.get("/{report_id}")
def get_report(report_id: str, db: Session = Depends(get_db)):
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return {"id": report.id, "case_id": report.case_id, "email_id": report.email_id,
            "generated_at": report.generated_at, "data": report.data}


@router.get("")
def list_reports(db: Session = Depends(get_db)):
    reports = db.query(models.Report).order_by(models.Report.generated_at.desc()).all()
    return [{"id": r.id, "case_id": r.case_id, "email_id": r.email_id, "generated_at": r.generated_at} for r in reports]
