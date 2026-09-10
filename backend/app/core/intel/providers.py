"""Intelligence provider abstraction.

`GeoIPProvider` / `DomainIntelProvider` define the interface. `DemoProvider`
implementations return deterministic, versioned fixture data and never touch
the network. `LiveProvider` implementations make real (free-tier, keyless)
lookups and are used only when INTEL_MODE=live; any failure or timeout falls
back to the Demo provider automatically, and the result's `source` field
always reflects what actually happened -- demo data is never relabeled as live.

Live implementations today:
  - Geolocation + hosting/provider info: ip-api.com free JSON endpoint (no key).
  - Domain registration + nameservers: RDAP via rdap.org (no key).
  - DNS/MX + SPF record: direct DNS queries via dnspython (no key, no
    third-party service at all -- this is the resolver every mail server uses).
There is currently NO live reputation/blacklist check for IPs or domains --
`reputation` is always "UNKNOWN" from the live path. See the module's callers
(app/api/routes_intel.py) for how this is surfaced; nothing here fabricates a
reputation value that wasn't actually determined.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import dns.resolver
import requests

from app.config import settings

FIXTURES_DIR = Path(__file__).parent / "fixtures"

DEMO_SOURCE = "Demo Intelligence Dataset"
LIVE_FALLBACK_SOURCE = "Demo Intelligence Dataset (live lookup unavailable, fell back automatically)"
LIVE_SOURCE_GEO = "Live Geolocation Provider (ip-api.com)"
LIVE_SOURCE_DOMAIN = "Live RDAP + DNS Lookup"
LIVE_SOURCE_DOMAIN_PARTIAL = "Live RDAP + DNS Lookup (partial -- some fields unavailable)"


def _load_fixture(name: str) -> dict:
    with open(FIXTURES_DIR / name, "r") as f:
        return json.load(f)


class GeoIPProvider(ABC):
    @abstractmethod
    def lookup(self, ip: str) -> dict[str, Any]:
        ...


class DomainIntelProvider(ABC):
    @abstractmethod
    def lookup(self, domain: str) -> dict[str, Any]:
        ...


class DemoGeoIPProvider(GeoIPProvider):
    def __init__(self):
        self._data = _load_fixture("ip_intel.json")

    def lookup(self, ip: str) -> dict[str, Any]:
        record = self._data.get(ip)
        if record:
            return {**record, "ip": ip, "source": DEMO_SOURCE}
        return {
            "ip": ip, "country": "Unknown", "region": "Unknown", "city": "Unknown",
            "lat": None, "lon": None, "isp": "Unknown", "asn": "Unknown", "org": "Unknown",
            "network_type": "UNKNOWN", "reputation": "UNKNOWN", "proxy_vpn_tor": "UNKNOWN",
            "source": DEMO_SOURCE + " (no fixture for this IP)",
        }


class DemoDomainIntelProvider(DomainIntelProvider):
    def __init__(self):
        self._data = _load_fixture("domain_intel.json")

    def lookup(self, domain: str) -> dict[str, Any]:
        record = self._data.get(domain)
        if record:
            return {**record, "domain": domain, "source": DEMO_SOURCE}
        return {
            "domain": domain, "registrar": "Unknown", "created_date": "Unknown",
            "nameservers": [], "mx": [], "spf_record": "", "reputation": "UNKNOWN",
            "source": DEMO_SOURCE + " (no fixture for this domain)",
        }


class LiveGeoIPProvider(GeoIPProvider):
    def __init__(self, fallback: GeoIPProvider):
        self._fallback = fallback

    def lookup(self, ip: str) -> dict[str, Any]:
        try:
            resp = requests.get(
                f"http://ip-api.com/json/{ip}",
                params={"fields": "status,country,regionName,city,lat,lon,isp,as,org,proxy,hosting,mobile"},
                timeout=2.5,
            )
            data = resp.json()
            if data.get("status") != "success":
                raise ValueError("live geoip lookup failed")
            if data.get("hosting"):
                network_type = "datacenter"
            elif data.get("mobile"):
                network_type = "mobile"
            else:
                network_type = "UNKNOWN"
            return {
                "ip": ip,
                "country": data.get("country", "Unknown"),
                "region": data.get("regionName", "Unknown"),
                "city": data.get("city", "Unknown"),
                "lat": data.get("lat"),
                "lon": data.get("lon"),
                "isp": data.get("isp", "Unknown"),
                "asn": data.get("as", "Unknown"),
                "org": data.get("org", "Unknown"),
                "network_type": network_type,
                "reputation": "UNKNOWN",
                "proxy_vpn_tor": "LIKELY_PROXY" if data.get("proxy") else "NO",
                "source": LIVE_SOURCE_GEO,
            }
        except Exception:
            result = self._fallback.lookup(ip)
            result["source"] = LIVE_FALLBACK_SOURCE
            return result


def _rdap_lookup(domain: str) -> dict[str, Any] | None:
    """Real RDAP registration lookup (rdap.org, no key). Returns None on any
    failure so the caller can tell "genuinely no data" apart from "empty"."""
    try:
        resp = requests.get(f"https://rdap.org/domain/{domain}", timeout=2.5)
        if resp.status_code != 200:
            return None
        data = resp.json()
        registrar = "Unknown"
        for entity in data.get("entities", []):
            if "registrar" in entity.get("roles", []):
                vcard = entity.get("vcardArray", [None, []])[1]
                for field in vcard:
                    if field[0] == "fn":
                        registrar = field[3]
        created_date = "Unknown"
        for event in data.get("events", []):
            if event.get("eventAction") == "registration":
                created_date = event.get("eventDate", "Unknown")
        nameservers = [ns.get("ldhName", "") for ns in data.get("nameservers", [])]
        return {"registrar": registrar, "created_date": created_date, "nameservers": nameservers}
    except Exception:
        return None


def _dns_mx_lookup(domain: str) -> list[str]:
    """Real DNS MX lookup (dnspython, direct to the resolver -- no third-party
    service, no key). Returns [] if the domain has no MX record or the query
    fails/times out."""
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=2.5)
        return [str(r.exchange).rstrip(".") for r in sorted(answers, key=lambda r: r.preference)]
    except Exception:
        return []


def _dns_spf_lookup(domain: str) -> str:
    """Real DNS TXT lookup, filtered for the SPF record. Returns "" if the
    domain has no SPF TXT record or the query fails/times out."""
    try:
        answers = dns.resolver.resolve(domain, "TXT", lifetime=2.5)
        for r in answers:
            txt = r.to_text().strip('"')
            if txt.lower().startswith("v=spf1"):
                return txt
        return ""
    except Exception:
        return ""


class LiveDomainIntelProvider(DomainIntelProvider):
    def __init__(self, fallback: DomainIntelProvider):
        self._fallback = fallback

    def lookup(self, domain: str) -> dict[str, Any]:
        rdap = _rdap_lookup(domain)
        mx = _dns_mx_lookup(domain)
        spf = _dns_spf_lookup(domain)

        # Only fall back to demo data when EVERY live source genuinely
        # produced nothing (e.g. no network access at all) -- a domain with
        # working DNS but no RDAP record (or vice versa) should surface the
        # real partial result rather than being silently replaced with
        # unrelated demo fixture data.
        if rdap is None and not mx and not spf:
            result = self._fallback.lookup(domain)
            result["source"] = LIVE_FALLBACK_SOURCE
            return result

        return {
            "domain": domain,
            "registrar": (rdap or {}).get("registrar", "Unknown"),
            "created_date": (rdap or {}).get("created_date", "Unknown"),
            "nameservers": (rdap or {}).get("nameservers", []),
            "mx": mx,
            "spf_record": spf,
            "reputation": "UNKNOWN",
            "source": LIVE_SOURCE_DOMAIN if rdap is not None else LIVE_SOURCE_DOMAIN_PARTIAL,
        }


def get_geoip_provider() -> GeoIPProvider:
    demo = DemoGeoIPProvider()
    if settings.intel_mode == "live":
        return LiveGeoIPProvider(fallback=demo)
    return demo


def get_domain_intel_provider() -> DomainIntelProvider:
    demo = DemoDomainIntelProvider()
    if settings.intel_mode == "live":
        return LiveDomainIntelProvider(fallback=demo)
    return demo
