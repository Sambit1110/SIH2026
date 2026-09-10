"""Regex/validation-based indicator-of-compromise extraction from parsed email content."""
from __future__ import annotations

import ipaddress
import re

import tldextract

IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IPV6_RE = re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}\b")
URL_RE = re.compile(r"\bhttps?://[^\s\"'<>\)\]]+", re.IGNORECASE)
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
DOMAIN_RE = re.compile(r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b")


def _valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def extract_ips(text: str) -> list[str]:
    found = set(IPV4_RE.findall(text)) | set(IPV6_RE.findall(text))
    return sorted({ip for ip in found if _valid_ip(ip)})


def extract_urls(text: str) -> list[str]:
    return sorted(set(URL_RE.findall(text)))


def extract_emails(text: str) -> list[str]:
    return sorted(set(m.lower() for m in EMAIL_RE.findall(text)))


def registered_domain(host: str) -> str:
    ext = tldextract.extract(host)
    if not ext.domain or not ext.suffix:
        return host.lower()
    return f"{ext.domain}.{ext.suffix}".lower()


def extract_domains(urls: list[str], emails: list[str], header_hosts: list[str]) -> list[str]:
    domains = set()
    for url in urls:
        host = re.sub(r"^https?://", "", url).split("/")[0].split(":")[0]
        if host and not _valid_ip(host):
            domains.add(registered_domain(host))
    for addr in emails:
        host = addr.split("@")[-1]
        domains.add(registered_domain(host))
    for host in header_hosts:
        if host and not _valid_ip(host) and DOMAIN_RE.fullmatch(host):
            domains.add(registered_domain(host))
    return sorted(domains)


def is_ip_literal_url(url: str) -> bool:
    host = re.sub(r"^https?://", "", url).split("/")[0].split(":")[0]
    return _valid_ip(host)
