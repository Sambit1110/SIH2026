"""Intelligence provider abstraction.

`GeoIPProvider` / `DomainIntelProvider` define the interface. `DemoProvider`
implementations return deterministic, versioned fixture data and never touch
the network. `LiveProvider` implementations make real (free-tier, keyless)
lookups and are used only when INTEL_MODE=live; any failure or timeout falls
back to the Demo provider automatically, and the result's `source` field
always reflects what actually happened -- demo data is never relabeled as live.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import requests

from app.config import settings

FIXTURES_DIR = Path(__file__).parent / "fixtures"

DEMO_SOURCE = "Demo Intelligence Dataset"
LIVE_FALLBACK_SOURCE = "Demo Intelligence Dataset (live lookup unavailable, fell back automatically)"
LIVE_SOURCE_GEO = "Live Geolocation Provider (ip-api.com)"
LIVE_SOURCE_DOMAIN = "Live RDAP/DNS Lookup"


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
                params={"fields": "status,country,regionName,city,lat,lon,isp,as,org,proxy"},
                timeout=2.5,
            )
            data = resp.json()
            if data.get("status") != "success":
                raise ValueError("live geoip lookup failed")
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
                "network_type": "UNKNOWN",
                "reputation": "UNKNOWN",
                "proxy_vpn_tor": "LIKELY_PROXY" if data.get("proxy") else "NO",
                "source": LIVE_SOURCE_GEO,
            }
        except Exception:
            result = self._fallback.lookup(ip)
            result["source"] = LIVE_FALLBACK_SOURCE
            return result


class LiveDomainIntelProvider(DomainIntelProvider):
    def __init__(self, fallback: DomainIntelProvider):
        self._fallback = fallback

    def lookup(self, domain: str) -> dict[str, Any]:
        try:
            resp = requests.get(f"https://rdap.org/domain/{domain}", timeout=2.5)
            if resp.status_code != 200:
                raise ValueError("rdap lookup failed")
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
            return {
                "domain": domain, "registrar": registrar, "created_date": created_date,
                "nameservers": nameservers, "mx": [], "spf_record": "",
                "reputation": "UNKNOWN", "source": LIVE_SOURCE_DOMAIN,
            }
        except Exception:
            result = self._fallback.lookup(domain)
            result["source"] = LIVE_FALLBACK_SOURCE
            return result


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
