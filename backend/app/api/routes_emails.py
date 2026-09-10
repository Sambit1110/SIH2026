from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import models
from app.api.deps import get_db
from app.config import settings
from app.core.graph.builder import build_email_graph
from app.core.parsing.email_parser import parse_eml_bytes, parse_raw_email_text
from app.core.parsing.ioc_extractor import registered_domain
from app.core.pipeline import analyze_email
from app.core.storage.providers import get_evidence_storage
from app.schemas import EmailAnalyzeRequest

router = APIRouter(prefix="/api/v1/emails", tags=["emails"])


def _store_evidence(db: Session, raw: bytes, filename: str, case_id: str | None) -> models.Evidence:
    sha256 = hashlib.sha256(raw).hexdigest()
    storage = get_evidence_storage()
    stored_path = storage.upload(filename, raw)

    evidence = models.Evidence(
        case_id=case_id,
        filename=filename,
        sha256=sha256,
        stored_path=stored_path,
        storage_provider=storage.name,
        size_bytes=len(raw),
        acquisition_method="Web Upload",
        analyst="System",
        integrity_status="VERIFIED",
    )
    db.add(evidence)
    db.flush()
    return evidence


def _validate_upload(filename: str, raw: bytes) -> None:
    ext = Path(filename or "").suffix.lower()
    if ext not in settings.allowed_upload_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'. Allowed: .eml, .txt")
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(status_code=400, detail="File exceeds maximum upload size of 10MB.")
    if len(raw) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")


@router.post("/upload")
async def upload_email(file: UploadFile = File(...), case_id: str | None = None, db: Session = Depends(get_db)):
    raw = await file.read()
    _validate_upload(file.filename or "upload.eml", raw)

    evidence = _store_evidence(db, raw, file.filename or "upload.eml", case_id)
    parsed = parse_eml_bytes(raw)
    email = analyze_email(db, parsed, case_id=case_id, evidence_id=evidence.id, label="Uploaded")
    return {"email_id": email.id, "evidence_id": evidence.id}


@router.post("/analyze")
async def analyze_raw_email(payload: EmailAnalyzeRequest, db: Session = Depends(get_db)):
    if not payload.raw_email.strip():
        raise HTTPException(status_code=400, detail="raw_email must not be empty.")
    raw = payload.raw_email.encode("utf-8", "replace")
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(status_code=400, detail="Raw email exceeds maximum size of 10MB.")

    evidence = _store_evidence(db, raw, "pasted_raw_email.eml", payload.case_id)
    parsed = parse_raw_email_text(payload.raw_email)
    email = analyze_email(db, parsed, case_id=payload.case_id, evidence_id=evidence.id, label="Uploaded")
    return {"email_id": email.id, "evidence_id": evidence.id}


def _get_email_or_404(db: Session, email_id: str) -> models.Email:
    email = db.query(models.Email).filter(models.Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found.")
    return email


def _email_summary(email: models.Email) -> dict:
    return {
        "id": email.id,
        "case_id": email.case_id,
        "from_addr": email.from_addr,
        "to_addr": email.to_addr,
        "subject": email.subject,
        "date_header": email.date_header,
        "label": email.label,
        "demo_case_key": email.demo_case_key,
        "created_at": email.created_at,
        "overall_score": email.analysis.overall_score if email.analysis else None,
        "severity": email.analysis.severity if email.analysis else None,
        "classification": email.analysis.classification if email.analysis else None,
    }


@router.get("")
def list_emails(db: Session = Depends(get_db)):
    emails = db.query(models.Email).order_by(models.Email.created_at.desc()).all()
    return [_email_summary(e) for e in emails]


@router.get("/{email_id}")
def get_email(email_id: str, db: Session = Depends(get_db)):
    email = _get_email_or_404(db, email_id)
    return {
        **_email_summary(email),
        "cc_addr": email.cc_addr,
        "reply_to": email.reply_to,
        "return_path": email.return_path,
        "message_id": email.message_id,
        "body_text": email.body_text,
        "body_html": email.body_html,
        "attachments": email.attachments,
        "evidence_id": email.evidence_id,
    }


@router.get("/{email_id}/headers")
def get_headers(email_id: str, db: Session = Depends(get_db)):
    email = _get_email_or_404(db, email_id)
    return {
        "raw_headers": email.raw_headers,
        "findings": email.analysis.header_findings if email.analysis else [],
    }


@router.get("/{email_id}/threat-analysis")
def get_threat_analysis(email_id: str, db: Session = Depends(get_db)):
    email = _get_email_or_404(db, email_id)
    if not email.analysis:
        raise HTTPException(status_code=404, detail="Analysis not available for this email.")
    a = email.analysis
    return {
        "overall_score": a.overall_score,
        "severity": a.severity,
        "classification": a.classification,
        "confidence": a.confidence,
        "sub_scores": a.sub_scores,
        "factors": a.factors,
        "lookalike_findings": a.lookalike_findings,
        "attribution": a.attribution,
    }


@router.get("/{email_id}/auth")
def get_auth(email_id: str, db: Session = Depends(get_db)):
    email = _get_email_or_404(db, email_id)
    if not email.auth_result:
        raise HTTPException(status_code=404, detail="Authentication analysis not available.")
    ar = email.auth_result
    return {
        "spf": ar.spf, "dkim": ar.dkim, "dmarc": ar.dmarc,
        "alignment": ar.alignment, "source": ar.source, "raw_auth_header": ar.raw_auth_header,
    }


@router.get("/{email_id}/iocs")
def get_iocs(email_id: str, db: Session = Depends(get_db)):
    _get_email_or_404(db, email_id)
    iocs = db.query(models.IOC).filter(models.IOC.email_id == email_id).all()
    return [
        {"id": i.id, "type": i.type, "value": i.value, "risk": i.risk, "confidence": i.confidence,
         "source": i.source, "extra": i.extra}
        for i in iocs
    ]


@router.get("/{email_id}/trace")
def get_trace(email_id: str, db: Session = Depends(get_db)):
    _get_email_or_404(db, email_id)
    hops = db.query(models.RelayHop).filter(models.RelayHop.email_id == email_id).order_by(models.RelayHop.sequence).all()
    enriched = []
    for hop in hops:
        ip_intel = None
        if hop.ip:
            ip_intel = db.query(models.IPIntel).filter(models.IPIntel.ip == hop.ip).first()
        enriched.append({
            "sequence": hop.sequence, "hostname": hop.hostname, "ip": hop.ip,
            "timestamp": hop.timestamp, "org": hop.org, "confidence": hop.confidence,
            "evidence_source": hop.evidence_source, "flags": hop.flags,
            "is_earliest_reliable": bool(hop.is_earliest_reliable),
            "geo": {
                "country": ip_intel.country, "region": ip_intel.region, "city": ip_intel.city,
                "lat": ip_intel.lat, "lon": ip_intel.lon, "isp": ip_intel.isp, "asn": ip_intel.asn,
                "org": ip_intel.org, "reputation": ip_intel.reputation, "source": ip_intel.source,
            } if ip_intel else None,
        })
    return enriched


@router.get("/{email_id}/graph")
def get_graph(email_id: str, db: Session = Depends(get_db)):
    email = _get_email_or_404(db, email_id)
    iocs = db.query(models.IOC).filter(models.IOC.email_id == email_id).all()
    ip_values = [i.value for i in iocs if i.type == "ip"]
    domain_values = [i.value for i in iocs if i.type == "domain"]
    url_objs = [type("U", (), {"url": i.value, "risk": i.risk, "reasons": i.extra.get("reasons", []) if i.extra else []}) for i in iocs if i.type == "url"]

    ip_records = [
        {"ip": r.ip, "country": r.country, "region": r.region, "city": r.city, "isp": r.isp,
         "asn": r.asn, "org": r.org, "reputation": r.reputation, "network_type": r.network_type,
         "proxy_vpn_tor": r.proxy_vpn_tor, "source": r.source}
        for r in db.query(models.IPIntel).filter(models.IPIntel.ip.in_(ip_values)).all()
    ]
    domain_records = [
        {"domain": r.domain, "registrar": r.registrar, "created_date": r.created_date,
         "nameservers": r.nameservers, "mx": r.mx, "reputation": r.reputation, "source": r.source}
        for r in db.query(models.DomainIntel).filter(models.DomainIntel.domain.in_(domain_values)).all()
    ]
    from_domain = registered_domain(email.from_addr.split("@")[-1]) if "@" in (email.from_addr or "") else ""

    return build_email_graph(
        email_id=email.id, from_addr=email.from_addr, reply_to=email.reply_to,
        from_domain=from_domain, ip_records=ip_records, domain_records=domain_records,
        url_findings=url_objs, mx_hosts=[],
    )


@router.get("/{email_id}/full")
def get_full_analysis(email_id: str, db: Session = Depends(get_db)):
    """One-call aggregate for the Email Analyzer page — the whole investigation
    surfaced together rather than assembled from disconnected requests."""
    email = _get_email_or_404(db, email_id)
    return {
        "email": get_email(email_id, db),
        "headers": get_headers(email_id, db),
        "threat_analysis": get_threat_analysis(email_id, db) if email.analysis else None,
        "auth": get_auth(email_id, db) if email.auth_result else None,
        "iocs": get_iocs(email_id, db),
        "trace": get_trace(email_id, db),
        "graph": get_graph(email_id, db),
        "evidence": (
            {
                "id": email.evidence_record.id, "filename": email.evidence_record.filename,
                "sha256": email.evidence_record.sha256, "size_bytes": email.evidence_record.size_bytes,
                "acquisition_method": email.evidence_record.acquisition_method,
                "integrity_status": email.evidence_record.integrity_status,
                "created_at": email.evidence_record.created_at,
            } if email.evidence_record else None
        ),
    }
