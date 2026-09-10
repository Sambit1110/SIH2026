from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.api.deps import get_db
from app.core.storage.providers import get_evidence_storage

router = APIRouter(prefix="/api/v1/evidence", tags=["evidence"])


@router.get("")
def list_evidence(db: Session = Depends(get_db)):
    items = db.query(models.Evidence).order_by(models.Evidence.created_at.desc()).all()
    return [
        {"id": e.id, "filename": e.filename, "sha256": e.sha256, "size_bytes": e.size_bytes,
         "acquisition_method": e.acquisition_method, "analyst": e.analyst,
         "integrity_status": e.integrity_status, "case_id": e.case_id, "created_at": e.created_at}
        for e in items
    ]


@router.get("/{evidence_id}")
def get_evidence(evidence_id: str, db: Session = Depends(get_db)):
    e = db.query(models.Evidence).filter(models.Evidence.id == evidence_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Evidence not found.")
    return {
        "id": e.id, "filename": e.filename, "sha256": e.sha256, "size_bytes": e.size_bytes,
        "acquisition_method": e.acquisition_method, "analyst": e.analyst,
        "integrity_status": e.integrity_status, "case_id": e.case_id, "created_at": e.created_at,
        "email_id": e.email.id if e.email else None,
    }


@router.post("/{evidence_id}/verify")
def verify_evidence(evidence_id: str, db: Session = Depends(get_db)):
    """Re-hashes the stored evidence file and confirms it matches the hash
    captured at ingestion -- the chain-of-custody integrity check."""
    e = db.query(models.Evidence).filter(models.Evidence.id == evidence_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Evidence not found.")

    storage = get_evidence_storage()
    content = storage.download(e.stored_path)
    if content is None:
        e.integrity_status = "MISSING"
        db.commit()
        return {"integrity_status": "MISSING", "detail": "Stored evidence file could not be located."}

    current_hash = hashlib.sha256(content).hexdigest()
    e.integrity_status = "VERIFIED" if current_hash == e.sha256 else "TAMPERED"
    db.commit()
    return {"integrity_status": e.integrity_status, "recorded_sha256": e.sha256, "current_sha256": current_hash}
