"""Schemas de achados de auditoria e investigações."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: str
    status: str
    severity: str
    title: str
    summary: str
    explanation: str | None = None
    methodology: str | None = None
    limitations: str | None = None
    metrics: dict | None = None
    evidence: list | None = None
    source_records: list | None = None
    confidence: float | None = None
    rule_code: str | None = None
    entity_id: int | None = None
    municipality_id: int | None = None
    supplier_id: int | None = None
    procurement_id: int | None = None
    contract_id: int | None = None
    created_at: datetime
    updated_at: datetime
    review_history: list | None = None


class FindingReview(BaseModel):
    status: str
    note: str | None = None


class ComparisonRequest(BaseModel):
    category_key: str | None = None
    unit: str | None = None
    item_id: int | None = None
    window_months: int = Field(default=18, ge=1, le=120)
    state_id: int | None = None


class InvestigationCreate(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    scope: dict | None = None


class InvestigationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=300)
    description: str | None = None
    status: str | None = None
    tags: list[str] | None = None
    scope: dict | None = None


class EvidenceCreate(BaseModel):
    kind: str
    title: str = Field(min_length=2, max_length=300)
    note: str | None = None
    reference_type: str | None = None
    reference_id: str | None = None
    source_url: str | None = None
    payload: dict | None = None


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    investigation_id: int
    kind: str
    title: str
    note: str | None = None
    reference_type: str | None = None
    reference_id: str | None = None
    source_url: str | None = None
    payload: dict | None = None
    created_at: datetime


class InvestigationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: str
    title: str
    description: str | None = None
    status: str
    tags: list | None = None
    scope: dict | None = None
    is_private: bool
    created_at: datetime
    updated_at: datetime


class InvestigationDetail(InvestigationOut):
    evidence_items: list[EvidenceOut] = Field(default_factory=list)
