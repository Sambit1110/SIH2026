"""Deterministic, explainable multi-signal risk scoring engine.

Six independently computed sub-scores (0-100), each backed by a list of
signed point contributions with a human-readable reason. The overall score
is a fixed weighted combination of the sub-scores -- there is no randomness
and no black-box model call anywhere in this module, so the same input
always produces the same score and the same explanation.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.detection.engine import DetectionResult
from app.core.detection.lookalike import LookalikeFinding
from app.core.detection.url_analysis import UrlFinding

CONTENT_CATEGORIES = {
    "Credential Harvesting", "Payment Diversion", "Invoice Fraud",
    "Gift Card Scam", "Urgency", "Secrecy", "Fear", "Malicious Link Language",
}
IMPERSONATION_DETECTION_CATEGORIES = {"Authority Pressure"}


@dataclass
class Factor:
    label: str
    points: int
    category: str
    reason: str


@dataclass
class ScoreResult:
    sub_scores: dict
    overall_score: float
    severity: str
    classification: str
    confidence: float
    factors: list[dict]
    attribution: dict


def _cap(value: float) -> float:
    return max(0.0, min(100.0, value))


def compute_risk_score(
    detection: DetectionResult,
    header_findings: list[dict],
    auth_result: dict,
    url_findings: list[UrlFinding],
    lookalike_findings: list[LookalikeFinding],
    from_domain_intel: dict | None,
    observed_ip_intel: list[dict],
    relay_flags: list[str],
) -> ScoreResult:
    factors: list[Factor] = []

    # --- Content risk: language-based social-engineering / fraud signals ---
    content_points = 0
    for s in detection.signals:
        if s.category in CONTENT_CATEGORIES:
            content_points += s.points
            factors.append(Factor(s.matched_phrase, s.points, "Content", s.reason))
    content_score = _cap(content_points)

    # --- Sender risk: header mismatches + sender domain reputation ---
    sender_points = 0
    for f in header_findings:
        if f["severity"] == "HIGH":
            pts = 15
        elif f["severity"] == "MEDIUM":
            pts = 10
        elif f["severity"] == "LOW":
            pts = 4
        else:
            continue
        sender_points += pts
        factors.append(Factor(f["issue"], pts, "Sender", f["detail"]))

    if from_domain_intel:
        rep = from_domain_intel.get("reputation")
        if rep == "MALICIOUS":
            sender_points += 25
            factors.append(Factor("Sender domain flagged malicious", 25, "Sender",
                                   f"{from_domain_intel.get('domain')} is flagged malicious in intelligence data."))
        elif rep == "SUSPICIOUS":
            sender_points += 15
            factors.append(Factor("Sender domain flagged suspicious", 15, "Sender",
                                   f"{from_domain_intel.get('domain')} is flagged suspicious (newly registered / anomalous records)."))
        if from_domain_intel.get("created_date", "Unknown") not in ("Unknown",):
            try:
                year = int(str(from_domain_intel["created_date"])[:4])
                if year >= 2025:
                    sender_points += 10
                    factors.append(Factor("Newly registered sender domain", 10, "Sender",
                                           f"Sender domain was registered on {from_domain_intel['created_date']}, "
                                           "very recently relative to typical legitimate correspondence."))
            except (ValueError, TypeError):
                pass
    sender_score = _cap(sender_points)

    # --- Authentication risk ---
    auth_points = 0
    if auth_result.get("spf") == "FAIL":
        auth_points += 25
        factors.append(Factor("SPF authentication failed", 25, "Authentication", "SPF check failed for sending infrastructure."))
    elif auth_result.get("spf") in ("NONE", "SOFTFAIL"):
        auth_points += 10
        factors.append(Factor(f"SPF result: {auth_result.get('spf')}", 10, "Authentication", "SPF did not pass cleanly."))
    if auth_result.get("dkim") == "FAIL":
        auth_points += 20
        factors.append(Factor("DKIM signature failed", 20, "Authentication", "DKIM signature validation failed."))
    elif auth_result.get("dkim") == "NONE":
        auth_points += 8
        factors.append(Factor("No DKIM signature", 8, "Authentication", "Message carries no DKIM signature."))
    if auth_result.get("dmarc") == "FAIL":
        auth_points += 25
        factors.append(Factor("DMARC failed", 25, "Authentication", "DMARC policy evaluation failed for this sender domain."))
    elif auth_result.get("dmarc") == "NONE":
        auth_points += 8
        factors.append(Factor("No DMARC result", 8, "Authentication", "No DMARC evaluation available for this message."))
    auth_score = _cap(auth_points)

    # --- URL risk ---
    url_points = 0
    for u in url_findings:
        per_reason = 7
        pts = min(30, per_reason * max(len(u.reasons), 1)) if u.reasons else 0
        if pts:
            url_points += pts
            factors.append(Factor(f"Suspicious URL: {u.url[:60]}", pts, "URL", "; ".join(u.reasons)))
    url_score = _cap(url_points)

    # --- Infrastructure risk ---
    infra_points = 0
    for ip_data in observed_ip_intel:
        rep = ip_data.get("reputation")
        if rep == "MALICIOUS":
            infra_points += 30
            factors.append(Factor(f"Malicious infrastructure: {ip_data.get('ip')}", 30, "Infrastructure",
                                   f"{ip_data.get('ip')} ({ip_data.get('org')}) is flagged malicious."))
        elif rep == "SUSPICIOUS":
            infra_points += 15
            factors.append(Factor(f"Suspicious infrastructure: {ip_data.get('ip')}", 15, "Infrastructure",
                                   f"{ip_data.get('ip')} ({ip_data.get('org')}) is flagged suspicious."))
        if ip_data.get("proxy_vpn_tor") == "LIKELY_PROXY":
            infra_points += 12
            factors.append(Factor(f"Anonymizing infrastructure indicator: {ip_data.get('ip')}", 12, "Infrastructure",
                                   "Observed IP shows proxy/VPN-like network characteristics."))
    if "TIMESTAMP_REGRESSION" in relay_flags:
        infra_points += 10
        factors.append(Factor("Relay chain timestamp anomaly", 10, "Infrastructure",
                               "Received-header timestamps are not monotonically increasing along the relay chain."))
    infra_score = _cap(infra_points)

    # --- Impersonation risk ---
    imp_points = 0
    for s in detection.signals:
        if s.category in IMPERSONATION_DETECTION_CATEGORIES:
            imp_points += s.points
            factors.append(Factor(s.matched_phrase, s.points, "Impersonation", s.reason))
    for lf in lookalike_findings:
        pts = {"HIGH": 35, "MEDIUM": 22, "LOW": 12}[lf.confidence]
        imp_points += pts
        factors.append(Factor(f"Lookalike domain: {lf.observed_domain}", pts, "Impersonation",
                               f"Resembles brand '{lf.target_brand}' ({lf.similarity}% similarity): {lf.reason}"))
    imp_score = _cap(imp_points)

    sub_scores = {
        "content": round(content_score, 1),
        "sender": round(sender_score, 1),
        "authentication": round(auth_score, 1),
        "url": round(url_score, 1),
        "infrastructure": round(infra_score, 1),
        "impersonation": round(imp_score, 1),
    }

    # Overall score is the scaled, capped SUM of every individual point
    # contribution recorded in `factors` above -- not a weighted average of
    # the six sub-scores. An average-of-sub-scores design silently punishes
    # attacks that legitimately don't touch every vector (a BEC email with no
    # URL at all has a correctly-zero URL sub-score, but that must not drag
    # down an otherwise overwhelming set of sender/content/auth signals).
    # Summing keeps the score directly traceable to the visible factor list
    # ("the score is exactly what you see added up below, capped at 100")
    # and SCALE is the one tunable constant controlling overall sensitivity.
    SCALE = 0.4
    raw_total = sum(f.points for f in factors)
    overall = round(_cap(raw_total * SCALE), 1)

    if overall >= 85:
        severity = "CRITICAL"
    elif overall >= 65:
        severity = "HIGH"
    elif overall >= 40:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    classification = _classify(detection, lookalike_findings, sub_scores, overall)

    corroborating = sum([
        auth_score >= 20,
        sender_score >= 15,
        infra_score >= 15,
        content_score >= 15,
        imp_score >= 15,
        url_score >= 10,
    ])
    confidence = round(min(97.0, 45.0 + corroborating * 9.0), 1)

    attribution = _build_attribution(sub_scores, lookalike_findings, observed_ip_intel, overall)

    factors_sorted = sorted(factors, key=lambda f: f.points, reverse=True)[:20]

    return ScoreResult(
        sub_scores=sub_scores,
        overall_score=overall,
        severity=severity,
        classification=classification,
        confidence=confidence,
        factors=[f.__dict__ for f in factors_sorted],
        attribution=attribution,
    )


def _classify(detection: DetectionResult, lookalike_findings: list[LookalikeFinding], sub_scores: dict, overall: float) -> str:
    """Classification is decided by presence of a specific, actionable
    technique signal (checked in priority order) rather than by whichever
    technique bucket happens to accumulate the most points -- a BEC email
    that also contains generic urgency/secrecy language (which buckets under
    "Social Engineering") must still classify as BEC, not get out-voted by
    its own supporting social-engineering signals.
    """
    totals = detection.technique_totals
    has_strong_lookalike = any(f.confidence in ("HIGH", "MEDIUM") for f in lookalike_findings)
    # Payment-diversion language alone doesn't distinguish "CEO wants a wire
    # transfer" (BEC) from "vendor wants their bank details updated" (invoice
    # fraud) -- executive-authority framing is the actual distinguishing
    # signal between the two, since both share the same financial-action
    # phrase bank.
    has_authority_signal = any(s.category == "Authority Pressure" for s in detection.signals)

    # Thresholds (not a bare ">0") guard against a single incidental phrase
    # match (e.g. "outstanding balance" appearing in an unrelated phishing
    # email) hijacking the classification away from a stronger, more
    # specific signal such as a confirmed lookalike domain.
    if overall < 25:
        return "Likely Legitimate"
    if totals.get("Business Email Compromise", 0) >= 14 and sub_scores["sender"] >= 15 and has_authority_signal:
        return "Business Email Compromise"
    if has_strong_lookalike and sub_scores["impersonation"] >= 30:
        return "Brand Impersonation / Lookalike Domain"
    if totals.get("Vendor Invoice Fraud", 0) >= 15:
        return "Vendor Invoice Fraud"
    if totals.get("Business Email Compromise", 0) >= 14 and sub_scores["sender"] >= 15:
        return "Vendor Invoice Fraud"
    if totals.get("Phishing", 0) >= 10:
        return "Credential Phishing"
    if totals.get("Fraud", 0) >= 10:
        return "Fraud"
    if totals.get("Social Engineering", 0) > 0:
        return "Suspicious - Social Engineering Indicators"
    return "Suspicious - Unclassified"


def _build_attribution(sub_scores: dict, lookalike_findings: list[LookalikeFinding], observed_ip_intel: list[dict], overall: float) -> dict:
    supporting = []
    conclusion = "Insufficient evidence for infrastructure attribution"
    evidence_strength = "WEAK"

    malicious_infra = [ip for ip in observed_ip_intel if ip.get("reputation") == "MALICIOUS"]
    suspicious_infra = [ip for ip in observed_ip_intel if ip.get("reputation") == "SUSPICIOUS"]
    proxy_infra = [ip for ip in observed_ip_intel if ip.get("proxy_vpn_tor") == "LIKELY_PROXY"]
    strong_lookalike = [f for f in lookalike_findings if f.confidence == "HIGH"]

    # Checked in descending order of evidence strength. A case can legitimately
    # land in the final "sender/auth only" branch when intelligence providers
    # have no reputation data for the observed infrastructure yet -- that must
    # still surface as real evidence, not "insufficient," when header forensics
    # and authentication both independently indicate spoofing.
    if malicious_infra:
        conclusion = "Probable malicious infrastructure"
        supporting.append(f"{len(malicious_infra)} observed IP(s) match known-malicious infrastructure indicators.")
        evidence_strength = "STRONG"
    elif strong_lookalike:
        conclusion = "Likely spoofed / impersonated domain"
        supporting.append("Sender or linked domain closely resembles a recognized brand domain.")
        evidence_strength = "STRONG"
    elif lookalike_findings:
        conclusion = "Likely spoofed / impersonated domain"
        supporting.append("Sender or linked domain closely resembles a recognized brand domain.")
        evidence_strength = "MODERATE"
    elif suspicious_infra:
        conclusion = "Suspicious infrastructure consistent with malicious activity"
        supporting.append(f"{len(suspicious_infra)} observed IP(s) are flagged suspicious in intelligence data.")
        evidence_strength = "MODERATE"
    elif proxy_infra:
        conclusion = "Anonymized infrastructure (proxy/VPN indicators observed)"
        supporting.append("Observed sending infrastructure shows proxy/VPN-like characteristics.")
        evidence_strength = "MODERATE"
    elif overall >= 65 and (sub_scores["sender"] >= 15 or sub_scores["authentication"] >= 20):
        conclusion = "Likely compromised or spoofed sender identity"
        evidence_strength = "MODERATE"
    elif overall < 25:
        conclusion = "Consistent with legitimate institutional infrastructure"
        evidence_strength = "MODERATE"
        supporting.append("No malicious infrastructure, spoofing, or anonymization indicators were observed.")

    if sub_scores["sender"] >= 15:
        supporting.append("Header forensics identified sender identity inconsistencies.")
    if sub_scores["authentication"] >= 20:
        supporting.append("Sender authentication (SPF/DKIM/DMARC) did not fully pass.")

    return {
        "conclusion": conclusion,
        "confidence": evidence_strength,
        "evidence_strength": evidence_strength,
        "supporting_indicators": supporting or ["No strong infrastructure-attribution indicators were observed."],
        "limitations": (
            "This assessment reflects observed technical infrastructure (IP addresses, hosting providers, "
            "domain registration data) and does not establish the physical identity or exact physical location "
            "of any individual. IP geolocation indicates approximate infrastructure location only. All "
            "conclusions are investigative leads, not legal findings."
        ),
    }
