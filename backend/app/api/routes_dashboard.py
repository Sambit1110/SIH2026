from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.api.deps import get_db
from app.config import settings

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    emails = db.query(models.Email).all()
    cases = db.query(models.Case).all()
    iocs_count = db.query(models.IOC).count()
    campaigns_count = db.query(models.Campaign).count()

    analyzed = [e for e in emails if e.analysis]
    critical = [e for e in analyzed if e.analysis.severity == "CRITICAL"]
    high = [e for e in analyzed if e.analysis.severity == "HIGH"]
    active_cases = [c for c in cases if c.status in ("Open", "Investigating")]

    classification_counts = Counter(e.analysis.classification for e in analyzed)
    severity_counts = Counter(e.analysis.severity for e in analyzed)

    recent_alerts = sorted(
        (e for e in analyzed if e.analysis.severity in ("CRITICAL", "HIGH")),
        key=lambda e: e.created_at, reverse=True,
    )[:8]

    recent_cases = sorted(cases, key=lambda c: c.updated_at, reverse=True)[:6]

    timeline_events = db.query(models.TimelineEvent).all()
    activity_by_day: Counter = Counter()
    for t in timeline_events:
        activity_by_day[t.occurred_at.date().isoformat()] += 1
    activity_series = sorted(activity_by_day.items())

    return {
        "intel_mode": settings.intel_mode,
        "metrics": {
            "emails_analyzed": len(analyzed),
            "critical_threats": len(critical),
            "high_risk_threats": len(high),
            "active_investigations": len(active_cases),
            "ioc_count": iocs_count,
            "campaign_count": campaigns_count,
            "total_cases": len(cases),
        },
        "threat_distribution": [{"classification": k, "count": v} for k, v in classification_counts.most_common()],
        "severity_distribution": [{"severity": k, "count": v} for k, v in severity_counts.most_common()],
        "recent_alerts": [
            {
                "id": e.id, "subject": e.subject, "from_addr": e.from_addr,
                "severity": e.analysis.severity, "overall_score": e.analysis.overall_score,
                "classification": e.analysis.classification, "created_at": e.created_at,
            }
            for e in recent_alerts
        ],
        "recent_investigations": [
            {"id": c.id, "case_number": c.case_number, "title": c.title, "status": c.status,
             "severity": c.severity, "updated_at": c.updated_at}
            for c in recent_cases
        ],
        "threat_activity_timeline": [{"date": d, "events": n} for d, n in activity_series[-14:]],
    }
