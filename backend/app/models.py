import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db import Base

# Renders as JSONB on Postgres (native, indexable, the Postgres-preferred
# JSON representation) and falls back to plain JSON on SQLite for local dev,
# where JSONB doesn't exist.
JSONType = JSON().with_variant(JSONB(), "postgresql")

# Always timezone-aware -- SQLite doesn't enforce this (it stores whatever
# you give it), but Postgres' TIMESTAMPTZ does, and every datetime this app
# produces is already UTC-aware via now() below, so this is a correctness
# fix as much as a Postgres-native preference: without timezone=True, a
# Postgres column would silently be TIMESTAMP WITHOUT TIME ZONE, and
# comparisons/serialization against the tz-aware Python values we actually
# store would be subtly wrong.
TZDateTime = DateTime(timezone=True)


def uid() -> str:
    return uuid.uuid4().hex[:12]


def now() -> datetime:
    return datetime.now(timezone.utc)


class Case(Base):
    __tablename__ = "cases"

    id = Column(String, primary_key=True, default=uid)
    case_number = Column(String, unique=True, index=True)
    title = Column(String, nullable=False)
    status = Column(String, default="Open", index=True)  # Open, Investigating, Contained, Resolved, Archived
    severity = Column(String, default="LOW")
    analyst = Column(String, default="Unassigned")
    summary = Column(Text, default="")
    notes = Column(JSONType, default=list)  # list[{author, text, created_at}]
    created_at = Column(TZDateTime, default=now)
    updated_at = Column(TZDateTime, default=now, onupdate=now)

    emails = relationship("Email", back_populates="case")
    evidence = relationship("Evidence", back_populates="case")
    timeline_events = relationship("TimelineEvent", back_populates="case")


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(String, primary_key=True, default=uid)
    case_id = Column(String, ForeignKey("cases.id"), nullable=True, index=True)
    filename = Column(String, nullable=False)
    sha256 = Column(String, nullable=False)
    # Opaque storage key resolved by the active EvidenceStorageProvider: a
    # local filesystem path (LocalStorageProvider, dev) or a Supabase
    # Storage object key (SupabaseStorageProvider, production).
    stored_path = Column(String, nullable=False)
    storage_provider = Column(String, default="local")  # "local" | "supabase"
    size_bytes = Column(Integer, default=0)
    acquisition_method = Column(String, default="Web Upload")
    analyst = Column(String, default="System")
    integrity_status = Column(String, default="VERIFIED")
    created_at = Column(TZDateTime, default=now)

    case = relationship("Case", back_populates="evidence")
    email = relationship("Email", back_populates="evidence_record", uselist=False)


class Email(Base):
    __tablename__ = "emails"

    id = Column(String, primary_key=True, default=uid)
    case_id = Column(String, ForeignKey("cases.id"), nullable=True, index=True)
    evidence_id = Column(String, ForeignKey("evidence.id"), nullable=True, index=True)

    from_addr = Column(String)
    to_addr = Column(String)
    cc_addr = Column(String)
    reply_to = Column(String)
    return_path = Column(String)
    subject = Column(String)
    date_header = Column(String)
    message_id = Column(String)

    raw_headers = Column(JSONType, default=list)  # [{name, value}]
    body_text = Column(Text, default="")
    body_html = Column(Text, default="")
    attachments = Column(JSONType, default=list)  # [{filename, size, mime, sha256}]

    demo_case_key = Column(String, nullable=True)  # e.g. "case-01" if seeded
    label = Column(String, default="Uploaded")  # Demo | Uploaded
    created_at = Column(TZDateTime, default=now, index=True)

    case = relationship("Case", back_populates="emails")
    evidence_record = relationship("Evidence", back_populates="email")
    analysis = relationship("AnalysisResult", back_populates="email", uselist=False)
    auth_result = relationship("AuthResult", back_populates="email", uselist=False)
    iocs = relationship("IOC", back_populates="email")
    relay_hops = relationship("RelayHop", back_populates="email", order_by="RelayHop.sequence")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(String, primary_key=True, default=uid)
    email_id = Column(String, ForeignKey("emails.id"), unique=True)
    overall_score = Column(Float)
    severity = Column(String, index=True)
    classification = Column(String)
    confidence = Column(Float)
    sub_scores = Column(JSONType)  # {content, sender, authentication, url, infrastructure, impersonation}
    factors = Column(JSONType)  # [{label, points, category, reason}]
    header_findings = Column(JSONType)  # [{issue, severity, detail}]
    lookalike_findings = Column(JSONType)  # [{observed_domain, target_brand, similarity, reason, confidence}]
    attribution = Column(JSONType)  # {conclusion, confidence, evidence_strength, supporting_indicators, limitations}
    created_at = Column(TZDateTime, default=now)

    email = relationship("Email", back_populates="analysis")


class AuthResult(Base):
    __tablename__ = "auth_results"

    id = Column(String, primary_key=True, default=uid)
    email_id = Column(String, ForeignKey("emails.id"), unique=True)
    spf = Column(String, default="NONE")
    dkim = Column(String, default="NONE")
    dmarc = Column(String, default="NONE")
    alignment = Column(JSONType, default=dict)
    source = Column(String, default="Reported by Receiving Mail Server")
    raw_auth_header = Column(Text, default="")

    email = relationship("Email", back_populates="auth_result")


class IOC(Base):
    __tablename__ = "iocs"

    id = Column(String, primary_key=True, default=uid)
    email_id = Column(String, ForeignKey("emails.id"), index=True)
    type = Column(String, index=True)  # ip, domain, url, email, hash, message_id, mx
    value = Column(String, index=True)
    risk = Column(String, default="LOW")
    confidence = Column(Float, default=0.5)
    source = Column(String, default="Header/Body Extraction")
    extra = Column(JSONType, default=dict)

    email = relationship("Email", back_populates="iocs")


class DomainIntel(Base):
    __tablename__ = "domain_intel"

    id = Column(String, primary_key=True, default=uid)
    domain = Column(String, unique=True, index=True)
    registrar = Column(String)
    created_date = Column(String)
    nameservers = Column(JSONType, default=list)
    mx = Column(JSONType, default=list)
    spf_record = Column(String, default="")
    reputation = Column(String, default="UNKNOWN")
    source = Column(String, default="Demo Intelligence Dataset")


class IPIntel(Base):
    __tablename__ = "ip_intel"

    id = Column(String, primary_key=True, default=uid)
    ip = Column(String, unique=True, index=True)
    country = Column(String)
    region = Column(String)
    city = Column(String)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    isp = Column(String)
    asn = Column(String)
    org = Column(String)
    network_type = Column(String, default="UNKNOWN")  # datacenter, residential, vpn, tor, corporate
    reputation = Column(String, default="UNKNOWN")
    proxy_vpn_tor = Column(String, default="UNKNOWN")
    source = Column(String, default="Demo Intelligence Dataset")


class RelayHop(Base):
    __tablename__ = "relay_hops"

    id = Column(String, primary_key=True, default=uid)
    email_id = Column(String, ForeignKey("emails.id"), index=True)
    sequence = Column(Integer)
    hostname = Column(String)
    ip = Column(String, nullable=True)
    timestamp = Column(String, nullable=True)
    org = Column(String, nullable=True)
    confidence = Column(String, default="MEDIUM")
    evidence_source = Column(String, default="Received Header")
    flags = Column(JSONType, default=list)  # e.g. ["PRIVATE_IP", "TIMESTAMP_ANOMALY"]
    is_earliest_reliable = Column(Integer, default=0)

    email = relationship("Email", back_populates="relay_hops")


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String, primary_key=True, default=uid)
    campaign_number = Column(String, unique=True)
    name = Column(String)
    technique = Column(String)
    confidence = Column(Float)
    shared_indicators = Column(JSONType, default=dict)  # {domains: [], ips: [], urls: []}
    created_at = Column(TZDateTime, default=now)

    members = relationship("CampaignEmail", back_populates="campaign")


class CampaignEmail(Base):
    __tablename__ = "campaign_emails"

    id = Column(String, primary_key=True, default=uid)
    campaign_id = Column(String, ForeignKey("campaigns.id"), index=True)
    email_id = Column(String, ForeignKey("emails.id"), index=True)

    campaign = relationship("Campaign", back_populates="members")


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id = Column(String, primary_key=True, default=uid)
    case_id = Column(String, ForeignKey("cases.id"), nullable=True, index=True)
    email_id = Column(String, ForeignKey("emails.id"), nullable=True, index=True)
    event_type = Column(String)
    description = Column(String)
    occurred_at = Column(TZDateTime, default=now)

    case = relationship("Case", back_populates="timeline_events")


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=uid)
    case_id = Column(String, ForeignKey("cases.id"), index=True)
    email_id = Column(String, ForeignKey("emails.id"), index=True)
    generated_at = Column(TZDateTime, default=now)
    data = Column(JSONType)
