"""URL risk analysis. Never fetches the URL (SSRF protection) -- purely static analysis
of the URL string itself."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from app.core.parsing.ioc_extractor import is_ip_literal_url

SUSPICIOUS_SCHEMES = {"data", "file", "javascript"}
URL_SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly"}
SUSPICIOUS_TLDS = {"xyz", "top", "click", "gq", "cf", "tk", "ml", "work"}


@dataclass
class UrlFinding:
    url: str
    risk: str
    reasons: list[str] = field(default_factory=list)


def analyze_url(url: str) -> UrlFinding:
    reasons: list[str] = []
    parsed = urlparse(url)

    if is_ip_literal_url(url):
        reasons.append("URL uses a raw IP address instead of a domain name")

    if parsed.scheme.lower() in SUSPICIOUS_SCHEMES:
        reasons.append(f"Uses uncommon/unsafe URI scheme '{parsed.scheme}'")

    if "%" in url and len(re.findall(r"%[0-9a-fA-F]{2}", url)) >= 3:
        reasons.append("Heavily percent-encoded URL, often used to obfuscate the destination")

    host = (parsed.hostname or "").lower()
    if host in URL_SHORTENERS:
        reasons.append(f"Uses URL shortening service '{host}', destination is not directly visible")

    tld = host.rsplit(".", 1)[-1] if "." in host else ""
    if tld in SUSPICIOUS_TLDS:
        reasons.append(f"Uses uncommon TLD '.{tld}' often associated with low-cost bulk registration")

    if host.count("-") >= 3:
        reasons.append("Domain contains an unusually high number of hyphens")

    if len(parsed.netloc) > 0 and any(c.isdigit() for c in host.replace(".", "")) and not is_ip_literal_url(url):
        digit_ratio = sum(c.isdigit() for c in host) / max(len(host), 1)
        if digit_ratio > 0.3:
            reasons.append("Domain name has an unusually high digit ratio")

    if parsed.path.count("/") > 5:
        reasons.append("Unusually deep URL path, potentially used to bury a phishing endpoint")

    if not reasons:
        risk = "LOW"
    elif len(reasons) == 1:
        risk = "MEDIUM"
    else:
        risk = "HIGH"

    return UrlFinding(url=url, risk=risk, reasons=reasons)


def analyze_urls(urls: list[str]) -> list[UrlFinding]:
    return [analyze_url(u) for u in urls]
