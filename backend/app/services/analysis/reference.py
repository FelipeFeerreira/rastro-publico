"""Construção de conjuntos de compras comparáveis e valores de referência.

Princípios:
- comparar apenas itens suficientemente equivalentes (mesma categoria e unidade);
- usar estatística robusta (mediana / IQR);
- registrar quais registros foram usados e por que são comparáveis;
- sempre declarar limitações e tamanho de amostra.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.procurement import Procurement, ProcurementItem, ProcurementResult
from app.services.analysis.statistics import Distribution

# Sinônimos de unidade para agrupar itens comparáveis.
_UNIT_ALIASES: dict[str, str] = {
    "un": "unidade", "und": "unidade", "unid": "unidade", "peca": "unidade",
    "pecas": "unidade", "cx": "caixa", "pct": "pacote", "l": "litro",
    "m": "metro", "m2": "metro2", "m3": "metro3", "h": "hora",
    "t": "tonelada", "g": "grama", "ml": "mililitro",
}

MIN_SAMPLE_SIZE = 5
DEFAULT_WINDOW_MONTHS = 18


def canonical_unit(unit: str | None) -> str | None:
    if not unit:
        return None
    key = unit.strip().lower().replace("²", "2").replace("³", "3")
    return _UNIT_ALIASES.get(key, key)


@dataclass
class ComparableDataset:
    category_key: str
    unit: str | None
    distribution: Distribution
    records: list[dict] = field(default_factory=list)
    methodology: str = ""
    limitations: str = ""

    @property
    def sample_size(self) -> int:
        return self.distribution.count

    @property
    def is_conclusive(self) -> bool:
        return self.sample_size >= MIN_SAMPLE_SIZE


def find_comparables(
    db: Session,
    *,
    category_key: str,
    unit: str | None,
    reference_date: date | None,
    window_months: int = DEFAULT_WINDOW_MONTHS,
    exclude_procurement_id: int | None = None,
    state_id: int | None = None,
    limit: int = 500,
) -> ComparableDataset:
    """Busca resultados de preço comparáveis ao item informado."""
    canonical = canonical_unit(unit)
    start = None
    if reference_date is not None:
        start = reference_date - timedelta(days=window_months * 30)

    stmt = (
        select(ProcurementResult, ProcurementItem, Procurement)
        .join(ProcurementItem, ProcurementResult.item_id == ProcurementItem.id)
        .join(Procurement, ProcurementResult.procurement_id == Procurement.id)
        .where(
            ProcurementItem.category_key == category_key,
            ProcurementResult.unit_price.is_not(None),
            ProcurementResult.unit_price > 0,
        )
    )
    if exclude_procurement_id is not None:
        stmt = stmt.where(Procurement.id != exclude_procurement_id)
    if start is not None:
        stmt = stmt.where(Procurement.published_at >= start)
    stmt = stmt.limit(limit * 4)

    rows = db.execute(stmt).all()

    comparable_records: list[dict] = []
    prices = []
    for result, item, procurement in rows:
        if canonical is not None and canonical_unit(item.unit) != canonical:
            continue
        prices.append(result.unit_price)
        comparable_records.append(
            {
                "result_id": result.id,
                "procurement_id": procurement.id,
                "pncp_control_number": procurement.pncp_control_number,
                "unit_price": float(result.unit_price) if result.unit_price is not None else None,
                "unit": item.unit,
                "quantity": float(result.quantity) if result.quantity else None,
                "date": result.result_date.isoformat() if result.result_date else None,
                "supplier": result.supplier_name,
                "source_url": result.source_url,
            }
        )
        if len(comparable_records) >= limit:
            break

    distribution = Distribution.from_values(prices)
    methodology = (
        f"Comparação por categoria '{category_key}'"
        + (f" e unidade '{canonical}'" if canonical else "")
        + f", janela de {window_months} meses"
        + (f" a partir de {start.isoformat()}" if start else "")
        + ". Método: mediana e intervalo interquartil (IQR)."
    )
    limitations = (
        "A comparabilidade depende de descrições e unidades informadas pelos órgãos. "
        "Diferenças de especificação, frete, prazo e condições contratuais podem "
        "não estar capturadas. Não há ajuste fino de especificação técnica."
    )
    return ComparableDataset(
        category_key=category_key,
        unit=canonical,
        distribution=distribution,
        records=comparable_records,
        methodology=methodology,
        limitations=limitations,
    )
