"""SPF / DKIM / DMARC analysis.

Primary source of truth is the Authentication-Results header already computed
by the receiving MTA -- this is labeled "Reported by Receiving Mail Server"
and is never fabricated. When that header is absent, the caller may supply
seeded Demo Intelligence (clearly labeled) so the UI still has something
meaningful to show for synthetic demo cases. We never silently invent a
live-looking result.
"""
from __future__ import annotations

import re

_RESULT_RE = re.compile(r"(spf|dkim|dmarc)\s*=\s*(\w+)", re.IGNORECASE)


def parse_authentication_results(header_value: str) -> dict:
    results = {"spf": "NONE", "dkim": "NONE", "dmarc": "NONE"}
    for mech, result in _RESULT_RE.findall(header_value or ""):
        results[mech.lower()] = result.upper()
    return results


def build_auth_result(auth_header: str, demo_fallback: dict | None = None) -> dict:
    if auth_header.strip():
        parsed = parse_authentication_results(auth_header)
        return {
            "spf": parsed["spf"],
            "dkim": parsed["dkim"],
            "dmarc": parsed["dmarc"],
            "alignment": {
                "spf_aligned": parsed["spf"] == "PASS",
                "dkim_aligned": parsed["dkim"] == "PASS",
            },
            "source": "Reported by Receiving Mail Server (Authentication-Results header)",
            "raw_auth_header": auth_header,
        }

    if demo_fallback:
        return {
            "spf": demo_fallback.get("spf", "NONE"),
            "dkim": demo_fallback.get("dkim", "NONE"),
            "dmarc": demo_fallback.get("dmarc", "NONE"),
            "alignment": demo_fallback.get(
                "alignment",
                {
                    "spf_aligned": demo_fallback.get("spf") == "PASS",
                    "dkim_aligned": demo_fallback.get("dkim") == "PASS",
                },
            ),
            "source": "Demo Intelligence Dataset (no Authentication-Results header present)",
            "raw_auth_header": "",
        }

    return {
        "spf": "NONE",
        "dkim": "NONE",
        "dmarc": "NONE",
        "alignment": {"spf_aligned": False, "dkim_aligned": False},
        "source": "Unavailable - no Authentication-Results header and no demo data",
        "raw_auth_header": "",
    }
