"""Header-level anomaly detection: mismatches, forged-looking fields, malformed headers."""
from __future__ import annotations

import re
from email.utils import parseaddr


def _domain_of(addr: str) -> str:
    return addr.split("@")[-1].lower().strip() if "@" in addr else ""


def analyze_headers(
    from_addr: str,
    reply_to: str,
    return_path: str,
    subject: str,
    message_id: str,
    date_header: str,
    x_headers: list[dict],
) -> list[dict]:
    """Returns a list of {issue, severity, detail} forensic findings."""
    findings: list[dict] = []

    from_domain = _domain_of(parseaddr(from_addr)[1] or from_addr)
    reply_domain = _domain_of(parseaddr(reply_to)[1] or reply_to) if reply_to else ""
    return_domain = _domain_of(parseaddr(return_path)[1] or return_path) if return_path else ""

    if reply_to and reply_domain and from_domain and reply_domain != from_domain:
        findings.append(
            {
                "issue": "Reply-To / From domain mismatch",
                "severity": "HIGH",
                "detail": f"From domain '{from_domain}' does not match Reply-To domain '{reply_domain}'. "
                "This is a common pattern in business email compromise, redirecting replies away from the "
                "apparent sender.",
            }
        )

    if return_path and return_domain and from_domain and return_domain != from_domain:
        findings.append(
            {
                "issue": "Return-Path / From domain mismatch",
                "severity": "MEDIUM",
                "detail": f"From domain '{from_domain}' does not match Return-Path domain '{return_domain}'. "
                "Bounce handling is directed to infrastructure other than the claimed sending domain.",
            }
        )

    if not message_id:
        findings.append(
            {
                "issue": "Missing Message-ID",
                "severity": "MEDIUM",
                "detail": "No Message-ID header was present. Legitimate mail transfer agents virtually always "
                "assign one; its absence is consistent with a hand-crafted or script-generated message.",
            }
        )
    elif message_id and from_domain and from_domain not in message_id.lower():
        findings.append(
            {
                "issue": "Message-ID domain does not reference sending domain",
                "severity": "LOW",
                "detail": f"Message-ID '{message_id}' does not reference the From domain '{from_domain}'. "
                "This is common but worth correlating with other signals.",
            }
        )

    if not date_header:
        findings.append(
            {
                "issue": "Missing Date header",
                "severity": "LOW",
                "detail": "No Date header was present in the message.",
            }
        )

    suspicious_subject_patterns = [
        (r"\bRE:\s*RE:", "Nested reply prefixes, often used to imply a prior conversation that never occurred."),
        (r"urgent|immediate action|action required", "Urgency language in the subject line, a common social-engineering pressure tactic."),
    ]
    for pattern, reason in suspicious_subject_patterns:
        if re.search(pattern, subject or "", re.IGNORECASE):
            findings.append(
                {
                    "issue": "Suspicious subject line pattern",
                    "severity": "LOW",
                    "detail": reason,
                }
            )

    interesting_x_headers = [h for h in x_headers if h["name"].lower() in (
        "x-originating-ip", "x-mailer", "x-sender-ip", "x-source-ip", "x-php-originating-script"
    )]
    for h in interesting_x_headers:
        findings.append(
            {
                "issue": f"Notable header present: {h['name']}",
                "severity": "INFO",
                "detail": f"{h['name']}: {h['value']}",
            }
        )

    if not findings:
        findings.append(
            {
                "issue": "No header anomalies detected",
                "severity": "INFO",
                "detail": "From, Reply-To, and Return-Path domains are consistent and required headers are present.",
            }
        )

    return findings
