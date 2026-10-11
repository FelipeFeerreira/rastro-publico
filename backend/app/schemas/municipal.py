"""Schemas de despesas municipais (TCE-SP)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


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
