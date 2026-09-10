from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.api.deps import get_db
from app.core.campaigns.correlation import recompute_campaigns

router = APIRouter(prefix="/api/v1/campaigns", tags=["campaigns"])


def _serialize(c: models.Campaign, db: Session) -> dict:
    member_ids = [m.email_id for m in c.members]
    emails = db.query(models.Email).filter(models.Email.id.in_(member_ids)).all()
    return {
        "id": c.id, "campaign_number": c.campaign_number, "name": c.name, "technique": c.technique,
        "confidence": c.confidence, "shared_indicators": c.shared_indicators, "created_at": c.created_at,
        "related_emails": [{"id": e.id, "subject": e.subject, "from_addr": e.from_addr} for e in emails],
    }


@router.get("")
def list_campaigns(db: Session = Depends(get_db)):
    campaigns = db.query(models.Campaign).order_by(models.Campaign.confidence.desc()).all()
    return [_serialize(c, db) for c in campaigns]


@router.get("/{campaign_id}")
def get_campaign(campaign_id: str, db: Session = Depends(get_db)):
    c = db.query(models.Campaign).filter(models.Campaign.id == campaign_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    return _serialize(c, db)


@router.post("/recompute")
def recompute(db: Session = Depends(get_db)):
    campaigns = recompute_campaigns(db)
    return {"campaign_count": len(campaigns)}
