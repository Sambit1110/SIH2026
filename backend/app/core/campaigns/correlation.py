"""Deterministic campaign correlation: groups emails that share IOCs
(domains/IPs/URLs) using connected components over a shared-indicator graph.
No ML clustering -- explainable, reproducible, and cheap to re-run.
"""
from __future__ import annotations

import ipaddress
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models import IOC, Campaign, CampaignEmail, Email


def _is_correlatable_ioc(ioc: IOC) -> bool:
    """Private/internal IPs (mail gateways, internal relay hops) are common
    to unrelated organizational traffic and must never be treated as shared
    attacker infrastructure -- correlating on them produces false campaign
    links between otherwise unrelated emails that merely passed through the
    same internal mail server.
    """
    if ioc.type != "ip":
        return True
    try:
        addr = ipaddress.ip_address(ioc.value)
        return not (addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved)
    except ValueError:
        return False


class _UnionFind:
    def __init__(self):
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


CORRELATABLE_TYPES = {"domain", "ip", "url"}


def recompute_campaigns(db: Session) -> list[Campaign]:
    emails = db.query(Email).all()
    if len(emails) < 2:
        return db.query(Campaign).all()

    uf = _UnionFind()
    indicator_to_emails: dict[str, set[str]] = defaultdict(set)

    for email in emails:
        uf.find(email.id)
        iocs = db.query(IOC).filter(IOC.email_id == email.id, IOC.type.in_(CORRELATABLE_TYPES)).all()
        for ioc in iocs:
            if not _is_correlatable_ioc(ioc):
                continue
            key = f"{ioc.type}:{ioc.value}"
            indicator_to_emails[key].add(email.id)

    shared_indicator_by_pair_key: dict[str, list[str]] = defaultdict(list)
    for key, email_ids in indicator_to_emails.items():
        if len(email_ids) < 2:
            continue
        ids = list(email_ids)
        first = ids[0]
        for other in ids[1:]:
            uf.union(first, other)
        for eid in ids:
            shared_indicator_by_pair_key[uf.find(eid)].append(key)

    groups: dict[str, list[str]] = defaultdict(list)
    for email in emails:
        groups[uf.find(email.id)].append(email.id)

    # Clear existing auto-generated campaign memberships and rebuild.
    db.query(CampaignEmail).delete()
    db.query(Campaign).delete()
    db.flush()

    campaigns = []
    counter = 1
    for root, member_ids in groups.items():
        if len(member_ids) < 2:
            continue
        shared_keys = set(shared_indicator_by_pair_key.get(root, []))
        shared_domains = sorted({k.split(":", 1)[1] for k in shared_keys if k.startswith("domain:")})
        shared_ips = sorted({k.split(":", 1)[1] for k in shared_keys if k.startswith("ip:")})
        shared_urls = sorted({k.split(":", 1)[1] for k in shared_keys if k.startswith("url:")})

        member_emails = [e for e in emails if e.id in member_ids]
        classifications = [e.analysis.classification for e in member_emails if e.analysis]
        primary_technique = max(set(classifications), key=classifications.count) if classifications else "Unclassified"

        confidence = min(97.0, 50.0 + len(shared_keys) * 8.0 + (len(member_ids) - 2) * 4.0)

        campaign = Campaign(
            campaign_number=f"TX-{counter:03d}",
            name=f"Campaign linked by {len(shared_keys)} shared indicator(s)",
            technique=primary_technique,
            confidence=round(confidence, 1),
            shared_indicators={"domains": shared_domains, "ips": shared_ips, "urls": shared_urls},
        )
        db.add(campaign)
        db.flush()
        for eid in member_ids:
            db.add(CampaignEmail(campaign_id=campaign.id, email_id=eid))
        campaigns.append(campaign)
        counter += 1

    db.commit()
    return campaigns
