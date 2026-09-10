"""Orchestrates the full DETECT pipeline for a single email: parse -> header
forensics -> auth analysis -> IOC extraction -> threat detection -> lookalike
-> URL analysis -> relay trace -> intelligence enrichment -> explainable
scoring -> persistence -> timeline events.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.detection.engine import classify
from app.core.detection.lookalike import analyze_domains
from app.core.detection.url_analysis import analyze_urls
from app.core.forensics.auth_analysis import build_auth_result
from app.core.forensics.header_forensics import analyze_headers
from app.core.forensics.relay_trace import reconstruct_relay_chain
from app.core.intel.providers import get_domain_intel_provider, get_geoip_provider
from app.core.parsing.email_parser import ParsedEmail
from app.core.parsing.ioc_extractor import (
    extract_domains,
    extract_emails,
    extract_ips,
    extract_urls,
    registered_domain,
)
from app.core.scoring.engine import compute_risk_score
from app import models


def analyze_email(
    db: Session,
    parsed: ParsedEmail,
    *,
    case_id: str | None,
    evidence_id: str | None,
    demo_case_key: str | None = None,
    demo_auth_fallback: dict | None = None,
    label: str = "Uploaded",
    base_time: datetime | None = None,
) -> models.Email:
    base_time = base_time or datetime.now(timezone.utc)

    email = models.Email(
        case_id=case_id,
        evidence_id=evidence_id,
        from_addr=parsed.from_addr,
        to_addr=parsed.to_addr,
        cc_addr=parsed.cc_addr,
        reply_to=parsed.reply_to,
        return_path=parsed.return_path,
        subject=parsed.subject,
        date_header=parsed.date_header,
        message_id=parsed.message_id,
        raw_headers=parsed.raw_headers,
        body_text=parsed.body_text,
        body_html=parsed.body_html,
        attachments=parsed.attachments,
        demo_case_key=demo_case_key,
        label=label,
        created_at=base_time,
    )
    db.add(email)
    db.flush()

    def timeline(event_type: str, description: str, offset_seconds: int) -> None:
        db.add(
            models.TimelineEvent(
                case_id=case_id,
                email_id=email.id,
                event_type=event_type,
                description=description,
                occurred_at=base_time + timedelta(seconds=offset_seconds),
            )
        )

    timeline("EMAIL_RECEIVED", "Email evidence ingested into Trace-X.", 0)

    # --- Header forensics ---
    header_findings = analyze_headers(
        parsed.from_addr, parsed.reply_to, parsed.return_path,
        parsed.subject, parsed.message_id, parsed.date_header, parsed.x_headers,
    )
    timeline("HEADERS_PARSED", f"Header forensics complete: {len(header_findings)} finding(s).", 2)

    # --- SPF / DKIM / DMARC ---
    auth_result = build_auth_result(parsed.auth_results_header, demo_fallback=demo_auth_fallback)
    db.add(models.AuthResult(email_id=email.id, **auth_result))
    timeline("AUTH_ANALYZED", f"Authentication analysis complete: SPF={auth_result['spf']}, "
             f"DKIM={auth_result['dkim']}, DMARC={auth_result['dmarc']}.", 4)

    # --- IOC extraction ---
    full_text = " ".join([parsed.subject, parsed.body_text, parsed.body_html])
    body_ips = extract_ips(full_text)
    header_ips = extract_ips(" ".join(parsed.received_headers))
    all_ips = sorted(set(body_ips) | set(header_ips))
    urls = extract_urls(full_text)
    emails_found = extract_emails(full_text)
    relay_hostnames = []

    relay_hops = reconstruct_relay_chain(parsed.received_headers)
    for hop in relay_hops:
        # Only treat a relay hop's hostname as an IOC-worthy domain when its
        # IP is public. A hop with a private/internal IP is, by definition,
        # infrastructure belonging to the receiving organization itself (its
        # own mail gateway) -- not attacker infrastructure -- so including
        # it here would falsely link every email that transits the same
        # internal mail server into one "campaign".
        if hop.hostname and hop.hostname != "unknown" and "PRIVATE_IP" not in hop.flags:
            relay_hostnames.append(hop.hostname)
        if hop.ip:
            all_ips.append(hop.ip)
    all_ips = sorted(set(all_ips))

    domains = extract_domains(urls, emails_found, relay_hostnames)
    from_domain = registered_domain(parsed.from_addr.split("@")[-1]) if "@" in parsed.from_addr else ""
    if from_domain and from_domain not in domains:
        domains.append(from_domain)

    iocs: list[models.IOC] = []
    for ip in all_ips:
        iocs.append(models.IOC(email_id=email.id, type="ip", value=ip, source="Header/Relay Extraction"))
    for d in domains:
        iocs.append(models.IOC(email_id=email.id, type="domain", value=d, source="Body/Header Extraction"))
    for u in urls:
        iocs.append(models.IOC(email_id=email.id, type="url", value=u, source="Body Extraction"))
    for e in emails_found:
        iocs.append(models.IOC(email_id=email.id, type="email", value=e, source="Body/Header Extraction"))
    if parsed.message_id:
        iocs.append(models.IOC(email_id=email.id, type="message_id", value=parsed.message_id, source="Header Extraction"))
    for att in parsed.attachments:
        iocs.append(models.IOC(email_id=email.id, type="hash", value=att["sha256"], source="Attachment Metadata",
                                extra={"filename": att["filename"], "mime": att["mime"]}))

    timeline("IOC_EXTRACTED", f"Extracted {len(iocs)} indicator(s) of compromise.", 6)

    # --- Threat detection (content) ---
    detection = classify(parsed.subject, parsed.body_text, parsed.body_html)
    timeline("THREAT_ENGINE_EXECUTED", f"Threat detection engine executed: dominant technique "
             f"'{detection.dominant_technique}'.", 8)

    # --- Lookalike domain detection ---
    lookalike_findings = analyze_domains(domains)

    # --- URL risk analysis ---
    url_findings = analyze_urls(urls)

    # --- Intelligence enrichment ---
    geo_provider = get_geoip_provider()
    domain_provider = get_domain_intel_provider()

    ip_intel_records = []
    for ip in all_ips:
        record = db.query(models.IPIntel).filter(models.IPIntel.ip == ip).first()
        if not record:
            data = geo_provider.lookup(ip)
            record = models.IPIntel(ip=ip, **{k: v for k, v in data.items() if k != "ip"})
            db.add(record)
            db.flush()
        ip_intel_records.append({
            "ip": record.ip, "country": record.country, "region": record.region, "city": record.city,
            "lat": record.lat, "lon": record.lon, "isp": record.isp, "asn": record.asn, "org": record.org,
            "network_type": record.network_type, "reputation": record.reputation,
            "proxy_vpn_tor": record.proxy_vpn_tor, "source": record.source,
        })

    domain_intel_records = {}
    for d in domains:
        record = db.query(models.DomainIntel).filter(models.DomainIntel.domain == d).first()
        if not record:
            data = domain_provider.lookup(d)
            record = models.DomainIntel(domain=d, **{k: v for k, v in data.items() if k != "domain"})
            db.add(record)
            db.flush()
        domain_intel_records[d] = {
            "domain": record.domain, "registrar": record.registrar, "created_date": record.created_date,
            "nameservers": record.nameservers, "mx": record.mx, "spf_record": record.spf_record,
            "reputation": record.reputation, "source": record.source,
        }

    timeline("INFRASTRUCTURE_INTEL_RETRIEVED",
             f"Retrieved intelligence for {len(all_ips)} IP(s) and {len(domains)} domain(s).", 10)

    # --- Relay hop persistence (with geo enrichment) ---
    relay_flags: list[str] = []
    for hop in relay_hops:
        geo = None
        if hop.ip:
            geo = next((r for r in ip_intel_records if r["ip"] == hop.ip), None)
        relay_flags.extend(hop.flags)
        db.add(models.RelayHop(
            email_id=email.id, sequence=hop.sequence, hostname=hop.hostname, ip=hop.ip,
            timestamp=hop.timestamp, org=hop.org, confidence=hop.confidence,
            evidence_source=hop.evidence_source, flags=hop.flags,
            is_earliest_reliable=1 if hop.is_earliest_reliable else 0,
        ))

    # --- Explainable scoring ---
    from_domain_intel = domain_intel_records.get(from_domain)
    score = compute_risk_score(
        detection=detection,
        header_findings=header_findings,
        auth_result=auth_result,
        url_findings=url_findings,
        lookalike_findings=lookalike_findings,
        from_domain_intel=from_domain_intel,
        observed_ip_intel=ip_intel_records,
        relay_flags=relay_flags,
    )
    timeline("RISK_SCORE_GENERATED",
             f"Risk score {score.overall_score}/100 ({score.severity}) - classified as '{score.classification}'.", 12)

    db.add(models.AnalysisResult(
        email_id=email.id,
        overall_score=score.overall_score,
        severity=score.severity,
        classification=score.classification,
        confidence=score.confidence,
        sub_scores=score.sub_scores,
        factors=score.factors,
        header_findings=header_findings,
        lookalike_findings=[lf.__dict__ for lf in lookalike_findings],
        attribution=score.attribution,
    ))

    for ioc in iocs:
        if ioc.type == "ip":
            match = next((r for r in ip_intel_records if r["ip"] == ioc.value), None)
            if match:
                ioc.risk = "HIGH" if match["reputation"] == "MALICIOUS" else ("MEDIUM" if match["reputation"] == "SUSPICIOUS" else "LOW")
                ioc.confidence = 0.9 if match["reputation"] != "UNKNOWN" else 0.4
        elif ioc.type == "domain":
            match = domain_intel_records.get(ioc.value)
            if match:
                ioc.risk = "HIGH" if match["reputation"] == "MALICIOUS" else ("MEDIUM" if match["reputation"] == "SUSPICIOUS" else "LOW")
                ioc.confidence = 0.9 if match["reputation"] != "UNKNOWN" else 0.4
        elif ioc.type == "url":
            match = next((u for u in url_findings if u.url == ioc.value), None)
            if match:
                ioc.risk = match.risk
                ioc.confidence = 0.85 if match.risk != "LOW" else 0.5
        db.add(ioc)

    if case_id:
        timeline("CASE_LINKED", "Email linked to investigation case.", 14)

    db.commit()
    db.refresh(email)
    return email
