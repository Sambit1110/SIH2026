"""Builds an infrastructure relationship graph for a single email, serialized
into React-Flow-compatible nodes/edges."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GraphNode:
    id: str
    type: str  # email, sender, reply_to, domain, ip, asn, url, mx, campaign
    label: str
    risk: str = "LOW"
    data: dict = field(default_factory=dict)


@dataclass
class GraphEdge:
    id: str
    source: str
    target: str
    relation: str


def build_email_graph(
    email_id: str,
    from_addr: str,
    reply_to: str,
    from_domain: str,
    ip_records: list[dict],
    domain_records: list[dict],
    url_findings: list,
    mx_hosts: list[str],
) -> dict:
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []

    email_node_id = f"email:{email_id}"
    nodes.append(GraphNode(id=email_node_id, type="email", label="Analyzed Email", risk="INFO"))

    if from_addr:
        sender_id = f"sender:{from_addr}"
        nodes.append(GraphNode(id=sender_id, type="sender", label=from_addr))
        edges.append(GraphEdge(id=f"e:{email_node_id}:{sender_id}", source=email_node_id, target=sender_id, relation="sent_from"))

    if reply_to and reply_to != from_addr:
        reply_id = f"reply_to:{reply_to}"
        nodes.append(GraphNode(id=reply_id, type="reply_to", label=reply_to, risk="MEDIUM"))
        edges.append(GraphEdge(id=f"e:{email_node_id}:{reply_id}", source=email_node_id, target=reply_id, relation="replies_route_to"))

    for d in domain_records:
        domain_id = f"domain:{d['domain']}"
        risk = "HIGH" if d.get("reputation") == "MALICIOUS" else ("MEDIUM" if d.get("reputation") == "SUSPICIOUS" else "LOW")
        nodes.append(GraphNode(id=domain_id, type="domain", label=d["domain"], risk=risk, data=d))
        if d["domain"] == from_domain and from_addr:
            edges.append(GraphEdge(id=f"e:sender:{domain_id}", source=f"sender:{from_addr}", target=domain_id, relation="uses_domain"))
        else:
            edges.append(GraphEdge(id=f"e:{email_node_id}:{domain_id}", source=email_node_id, target=domain_id, relation="references_domain"))
        for mx in d.get("mx", []):
            mx_id = f"mx:{mx}"
            nodes.append(GraphNode(id=mx_id, type="mx", label=mx))
            edges.append(GraphEdge(id=f"e:{domain_id}:{mx_id}", source=domain_id, target=mx_id, relation="mail_exchanger"))

    for ip in ip_records:
        ip_id = f"ip:{ip['ip']}"
        risk = "HIGH" if ip.get("reputation") == "MALICIOUS" else ("MEDIUM" if ip.get("reputation") == "SUSPICIOUS" else "LOW")
        nodes.append(GraphNode(id=ip_id, type="ip", label=ip["ip"], risk=risk, data=ip))
        edges.append(GraphEdge(id=f"e:{email_node_id}:{ip_id}", source=email_node_id, target=ip_id, relation="observed_relay_ip"))
        if ip.get("asn") and ip["asn"] not in ("N/A", "Unknown"):
            asn_id = f"asn:{ip['asn']}"
            nodes.append(GraphNode(id=asn_id, type="asn", label=f"{ip['asn']} ({ip.get('org', '')})"))
            edges.append(GraphEdge(id=f"e:{ip_id}:{asn_id}", source=ip_id, target=asn_id, relation="belongs_to_asn"))

    for u in url_findings:
        url_id = f"url:{u.url}"
        risk = u.risk
        nodes.append(GraphNode(id=url_id, type="url", label=u.url[:50], risk=risk, data={"reasons": u.reasons}))
        edges.append(GraphEdge(id=f"e:{email_node_id}:{url_id}", source=email_node_id, target=url_id, relation="contains_url"))

    seen_ids = set()
    dedup_nodes = []
    for n in nodes:
        if n.id not in seen_ids:
            seen_ids.add(n.id)
            dedup_nodes.append(n)

    return {
        "nodes": [n.__dict__ for n in dedup_nodes],
        "edges": [e.__dict__ for e in edges],
    }
