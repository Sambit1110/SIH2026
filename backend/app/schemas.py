from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CaseCreate(BaseModel):
    title: str
    severity: str = "LOW"
    analyst: str = "Unassigned"
    summary: str = ""


class CaseUpdate(BaseModel):
    title: str | None = None
    status: str | None = None
    severity: str | None = None
    analyst: str | None = None
    summary: str | None = None


class NoteCreate(BaseModel):
    author: str
    text: str


class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_number: str
    title: str
    status: str
    severity: str
    analyst: str
    summary: str
    notes: list
    created_at: datetime
    updated_at: datetime


class EmailAnalyzeRequest(BaseModel):
    raw_email: str
    case_id: str | None = None


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    filename: str
    sha256: str
    size_bytes: int
    acquisition_method: str
    analyst: str
    integrity_status: str
    created_at: datetime


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    campaign_number: str
    name: str
    technique: str
    confidence: float
    shared_indicators: dict
    created_at: datetime
