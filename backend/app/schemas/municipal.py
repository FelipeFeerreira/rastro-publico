"""Schemas de despesas municipais (TCE-SP)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MunicipalExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    municipality_id: int
    entity_id: int | None = None
    entity_name: str | None = None
    supplier_id: int | None = None
    supplier_name: str | None = None
    supplier_document: str | None = None
    empenho_number: str | None = None
    stage: str
    value: Decimal | None = None
    event_year: int | None = None
    event_month: int | None = None
    month_name: str | None = None
    event_date: date | None = None
    description: str | None = None
    source_url: str | None = None
    collected_at: datetime | None = None


class MunicipalCoverage(BaseModel):
    """Período efetivamente coberto pelos dados importados."""

    first_date: date | None = None
    last_date: date | None = None
    last_collected_at: datetime | None = None
    # Meses com dados por ano — ex.: {"2025": [1..12], "2026": [1..8]}.
    months_by_year: dict[str, list[int]] = Field(default_factory=dict)
    # Anos com menos de 12 meses (cobertura parcial).
    partial_years: list[int] = Field(default_factory=list)


class MunicipalExpenseTotals(BaseModel):
    """Totais por estágio. Estágios nunca são somados como se fossem o mesmo.

    `committed_net` = empenhado + reforço − anulação (o valor empenhado líquido).
    """

    records: int = 0
    empenhado: Decimal = Decimal("0")
    liquidado: Decimal = Decimal("0")
    pago: Decimal = Decimal("0")
    reforco: Decimal = Decimal("0")
    anulacao: Decimal = Decimal("0")
    committed_net: Decimal = Decimal("0")
    coverage: MunicipalCoverage | None = None


class MunicipalInstitutionTotals(BaseModel):
    """Totais por instituição responsável (Prefeitura, Câmara, SAAE)."""

    entity_id: int | None = None
    entity_name: str | None = None
    records: int = 0
    empenhado: Decimal = Decimal("0")
    liquidado: Decimal = Decimal("0")
    pago: Decimal = Decimal("0")
    reforco: Decimal = Decimal("0")
    anulacao: Decimal = Decimal("0")
    committed_net: Decimal = Decimal("0")
