"""Schemas de agentes públicos e remuneração."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RemunerationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    reference_year: int | None = None
    reference_month: int | None = None
    gross_amount: Decimal | None = None
    net_amount: Decimal | None = None
    deductions: Decimal | None = None
    reference_date: date | None = None
    source_url: str | None = None


class PersonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    masked_document: str | None = None
    entity_id: int | None = None
    entity_name: str | None = None
    role_title: str | None = None
    source_url: str | None = None
    # Última remuneração conhecida, quando oficialmente disponível.
    latest_gross: Decimal | None = None
    latest_net: Decimal | None = None
    latest_reference_year: int | None = None
    latest_reference_month: int | None = None


class PersonDetail(PersonOut):
    remunerations: list[RemunerationOut] = Field(default_factory=list)


class SourceAvailability(BaseModel):
    code: str
    name: str
    status: str
    supports_salary: bool
    credentials_required: bool
    credentials_present: bool
    note: str
