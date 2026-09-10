from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.api.deps import get_db
from app.config import settings
from app.core.intel.providers import get_domain_intel_provider, get_geoip_provider

router = APIRouter(prefix="/api/v1", tags=["intelligence"])


@router.get("/ip/{ip}")
def lookup_ip(ip: str, db: Session = Depends(get_db)):
    record = db.query(models.IPIntel).filter(models.IPIntel.ip == ip).first()
    if record:
        return {
            "ip": record.ip, "country": record.country, "region": record.region, "city": record.city,
            "lat": record.lat, "lon": record.lon, "isp": record.isp, "asn": record.asn, "org": record.org,
            "network_type": record.network_type, "reputation": record.reputation,
            "proxy_vpn_tor": record.proxy_vpn_tor, "source": record.source, "cached": True,
        }
    data = get_geoip_provider().lookup(ip)
    return {**data, "cached": False}


@router.get("/domains/{domain}")
def lookup_domain(domain: str, db: Session = Depends(get_db)):
    record = db.query(models.DomainIntel).filter(models.DomainIntel.domain == domain).first()
    if record:
        return {
            "domain": record.domain, "registrar": record.registrar, "created_date": record.created_date,
            "nameservers": record.nameservers, "mx": record.mx, "spf_record": record.spf_record,
            "reputation": record.reputation, "source": record.source, "cached": True,
        }
    data = get_domain_intel_provider().lookup(domain)
    return {**data, "cached": False}


@router.get("/iocs")
def list_all_iocs(db: Session = Depends(get_db)):
    iocs = db.query(models.IOC).order_by(models.IOC.id.desc()).limit(500).all()
    return [
        {"id": i.id, "email_id": i.email_id, "type": i.type, "value": i.value,
         "risk": i.risk, "confidence": i.confidence, "source": i.source}
        for i in iocs
    ]


@router.get("/settings")
def get_settings():
    return {"intel_mode": settings.intel_mode, "app_name": settings.app_name}
