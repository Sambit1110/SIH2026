"""Assembles the 19-section structured forensic report from already-computed
data -- pure aggregation, no new analysis performed here."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app import models


def build_report(db: Session, case: models.Case, email: models.Email) -> dict:
    analysis = email.analysis
    auth = email.auth_result
    iocs = db.query(models.IOC).filter(models.IOC.email_id == email.id).all()
    hops = db.query(models.RelayHop).filter(models.RelayHop.email_id == email.id).order_by(models.RelayHop.sequence).all()
    timeline = (
        db.query(models.TimelineEvent)
        .filter(models.TimelineEvent.email_id == email.id)
        .order_by(models.TimelineEvent.occurred_at)
        .all()
    )
    evidence = email.evidence_record

    domain_iocs = [i.value for i in iocs if i.type == "domain"]
    ip_iocs = [i.value for i in iocs if i.type == "ip"]
    url_iocs = [i.value for i in iocs if i.type == "url"]

    domain_intel = db.query(models.DomainIntel).filter(models.DomainIntel.domain.in_(domain_iocs)).all()
    ip_intel = db.query(models.IPIntel).filter(models.IPIntel.ip.in_(ip_iocs)).all()

    return {
        "case_information": {
            "case_number": case.case_number, "title": case.title, "status": case.status,
            "severity": case.severity, "analyst": case.analyst, "created_at": case.created_at.isoformat(),
        },
        "executive_summary": (
            f"Email '{email.subject}' from {email.from_addr} was analyzed and classified as "
            f"{analysis.classification if analysis else 'Unclassified'} with an overall risk score of "
            f"{analysis.overall_score if analysis else 'N/A'}/100 "
            f"({analysis.severity if analysis else 'N/A'} severity, "
            f"{analysis.confidence if analysis else 'N/A'}% confidence)."
        ) if analysis else "Analysis not available for this email.",
        "email_metadata": {
            "from": email.from_addr, "to": email.to_addr, "cc": email.cc_addr, "reply_to": email.reply_to,
            "return_path": email.return_path, "subject": email.subject, "date": email.date_header,
            "message_id": email.message_id,
        },
        "threat_classification": {
            "classification": analysis.classification if analysis else None,
            "confidence": analysis.confidence if analysis else None,
        },
        "risk_score": {
            "overall_score": analysis.overall_score if analysis else None,
            "severity": analysis.severity if analysis else None,
            "sub_scores": analysis.sub_scores if analysis else None,
            "factors": analysis.factors if analysis else [],
        },
        "authentication_analysis": {
            "spf": auth.spf, "dkim": auth.dkim, "dmarc": auth.dmarc, "alignment": auth.alignment,
            "source": auth.source,
        } if auth else None,
        "header_analysis": analysis.header_findings if analysis else [],
        "ioc_findings": [{"type": i.type, "value": i.value, "risk": i.risk, "confidence": i.confidence, "source": i.source} for i in iocs],
        "url_analysis": [i.value for i in iocs if i.type == "url"],
        "domain_intelligence": [
            {"domain": d.domain, "registrar": d.registrar, "created_date": d.created_date,
             "nameservers": d.nameservers, "mx": d.mx, "reputation": d.reputation, "source": d.source}
            for d in domain_intel
        ],
        "ip_intelligence": [
            {"ip": i.ip, "country": i.country, "region": i.region, "city": i.city, "isp": i.isp,
             "asn": i.asn, "org": i.org, "reputation": i.reputation, "proxy_vpn_tor": i.proxy_vpn_tor,
             "source": i.source}
            for i in ip_intel
        ],
        "relay_trace": [
            {"sequence": h.sequence, "hostname": h.hostname, "ip": h.ip, "timestamp": h.timestamp,
             "org": h.org, "confidence": h.confidence, "flags": h.flags,
             "is_earliest_reliable": bool(h.is_earliest_reliable)}
            for h in hops
        ],
        "geolocation": [
            {"ip": i.ip, "country": i.country, "region": i.region, "city": i.city, "lat": i.lat, "lon": i.lon,
             "source": i.source}
            for i in ip_intel if i.lat is not None
        ],
        "infrastructure_relationships": "See Infrastructure Graph in the Trace-X platform for the interactive view.",
        "timeline": [
            {"event_type": t.event_type, "description": t.description, "occurred_at": t.occurred_at.isoformat()}
            for t in timeline
        ],
        "evidence_integrity": {
            "evidence_id": evidence.id, "filename": evidence.filename, "sha256": evidence.sha256,
            "acquisition_method": evidence.acquisition_method, "integrity_status": evidence.integrity_status,
            "created_at": evidence.created_at.isoformat(),
        } if evidence else None,
        "attribution_assessment": analysis.attribution if analysis else None,
        "confidence_levels": {
            "classification_confidence": analysis.confidence if analysis else None,
            "attribution_evidence_strength": analysis.attribution.get("evidence_strength") if analysis else None,
        },
        "recommended_actions": _recommended_actions(analysis),
    }


def _recommended_actions(analysis) -> list[str]:
    if not analysis:
        return ["Insufficient analysis data to generate recommendations."]
    actions = []
    if analysis.severity in ("CRITICAL", "HIGH"):
        actions.append("Quarantine or block further delivery from the observed sender domain and IP infrastructure pending review.")
        actions.append("Notify the targeted recipient(s) and any impersonated party (e.g. the executive or vendor referenced).")
        actions.append("Do not action any payment, credential, or account-change request contained in this message.")
    if analysis.sub_scores.get("authentication", 0) >= 20:
        actions.append("Review and tighten SPF/DKIM/DMARC enforcement policy for the organization's own domain(s).")
    if analysis.sub_scores.get("impersonation", 0) >= 20:
        actions.append("Consider defensive domain registration or monitoring for close lookalikes of impersonated brand(s).")
    if analysis.severity == "LOW":
        actions.append("No immediate action required; retain for baseline reference.")
    actions.append("Preserve original evidence and chain-of-custody records for potential escalation.")
    return actions
