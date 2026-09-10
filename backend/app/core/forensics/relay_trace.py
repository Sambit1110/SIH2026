"""Reconstructs the mail relay path from Received headers into a chronological forensic trace.

Received headers are prepended by each hop, so the header block's LAST entry
(closest to the bottom of the raw source) is the EARLIEST hop chronologically.
We parse each header, order by parsed timestamp (falling back to header order
when timestamps are missing/unparseable), and flag anomalies along the way.
"""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import parsedate_to_datetime

FROM_RE = re.compile(r"from\s+([^\s]+)", re.IGNORECASE)
PAREN_RE = re.compile(r"\(([^)]*)\)")
BY_RE = re.compile(r"\bby\s+([^\s;]+)", re.IGNORECASE)
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IPV6_RE = re.compile(r"\b[0-9a-fA-F]{1,4}(?::[0-9a-fA-F]{0,4}){2,7}\b")


@dataclass
class RelayHopResult:
    sequence: int
    hostname: str
    ip: str | None
    timestamp: str | None
    parsed_dt: datetime | None
    org: str | None
    confidence: str
    evidence_source: str
    flags: list[str] = field(default_factory=list)
    is_earliest_reliable: bool = False


def _extract_ip(segment: str) -> str | None:
    for pat in (IPV4_RE, IPV6_RE):
        m = pat.search(segment)
        if m:
            candidate = m.group(0)
            try:
                ipaddress.ip_address(candidate)
                return candidate
            except ValueError:
                continue
    return None


def _is_private(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        return False


def _parse_one(raw_header: str, header_index: int) -> RelayHopResult:
    from_match = FROM_RE.search(raw_header)
    hostname = from_match.group(1) if from_match else "unknown"

    paren_content = " ".join(PAREN_RE.findall(raw_header))
    ip = _extract_ip(paren_content) or _extract_ip(raw_header)

    by_match = BY_RE.search(raw_header)
    by_host = by_match.group(1) if by_match else None

    timestamp_part = raw_header.split(";")[-1].strip() if ";" in raw_header else ""
    parsed_dt = None
    if timestamp_part:
        try:
            parsed_dt = parsedate_to_datetime(timestamp_part)
        except (TypeError, ValueError):
            parsed_dt = None

    flags: list[str] = []
    if ip and _is_private(ip):
        flags.append("PRIVATE_IP")
    if not ip:
        flags.append("NO_IP_OBSERVED")
    if not parsed_dt:
        flags.append("UNPARSEABLE_TIMESTAMP")

    confidence = "HIGH" if ip and parsed_dt else ("MEDIUM" if ip else "LOW")

    return RelayHopResult(
        sequence=0,  # assigned after ordering
        hostname=hostname,
        ip=ip,
        timestamp=timestamp_part or None,
        parsed_dt=parsed_dt,
        org=by_host,
        confidence=confidence,
        evidence_source="Received Header",
        flags=flags,
    )


def reconstruct_relay_chain(received_headers: list[str]) -> list[RelayHopResult]:
    """`received_headers` is in header order (index 0 = most recent / closest to recipient)."""
    if not received_headers:
        return []

    # Reverse so index 0 = earliest hop (closest to true origin), matching wire order.
    chronological_raw = list(reversed(received_headers))
    hops = [_parse_one(h, i) for i, h in enumerate(chronological_raw)]

    # Detect timestamp regressions (a later hop timestamped earlier than an
    # earlier hop is a routing/anomaly signal, not necessarily malicious, but
    # worth flagging for the analyst).
    last_dt = None
    for hop in hops:
        if hop.parsed_dt and last_dt and hop.parsed_dt < last_dt:
            hop.flags.append("TIMESTAMP_REGRESSION")
        if hop.parsed_dt:
            last_dt = hop.parsed_dt

    for i, hop in enumerate(hops, start=1):
        hop.sequence = i

    # Earliest reliable observed node: first hop (in chronological order) with
    # a public IP and no missing-timestamp flag. Never assert it's the "true"
    # origin — just the earliest node we can observe with reasonable confidence.
    for hop in hops:
        if hop.ip and "PRIVATE_IP" not in hop.flags and hop.confidence in ("HIGH", "MEDIUM"):
            hop.is_earliest_reliable = True
            break

    return hops
