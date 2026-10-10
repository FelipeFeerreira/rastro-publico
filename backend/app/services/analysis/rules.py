"""Regras determinísticas de detecção de anomalias.

Cada regra recebe dados já normalizados e devolve candidatos a achado com
métricas, evidências, metodologia e limitações. As regras são conservadoras:
preferem não sinalizar a produzir falsos positivos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.enums import FindingSeverity
from app.models.procurement import Procurement, ProcurementItem
from app.services.analysis.reference import ComparableDataset
from app.services.analysis.statistics import median, modified_zscore

MIN_SAMPLE = 5
OUTLIER_IQR_FACTOR = 1.5
OUTLIER_MIN_RATIO = 1.3
ZSCORE_THRESHOLD = 3.5


@dataclass
class FindingCandidate:
    rule_code: str
    title: str
    summary: str
    explanation: str
    methodology: str
    limitations: str
    severity: FindingSeverity
    metrics: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    source_records: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.5


def _pct_diff(value: float, reference: float) -> float:
    if reference == 0:
        return 0.0
    return (value - reference) / reference * 100.0


def rule_unit_price_outlier(
    item: ProcurementItem, comparables: ComparableDataset
) -> FindingCandidate | None:
    """Preço unitário muito acima do padrão de itens equivalentes."""
    if not comparables.is_conclusive:
        return None

    prices = [r["unit_price"] for r in comparables.records if r["unit_price"]]
    if not prices:
        return None

    # Preço do item: usa o menor resultado homologado do item (mais favorável).
    results = [r for r in item.results if r.unit_price is not None]
    if not results:
        return None
    target = min(results, key=lambda r: r.unit_price)  # type: ignore[arg-type]
    value = float(target.unit_price)

    dist = comparables.distribution
    med = dist.median or median(prices)
    if med is None:
        return None
    iqr = dist.iqr
    threshold = (dist.p75 + OUTLIER_IQR_FACTOR * iqr) if (dist.p75 and iqr) else None
    ratio = value / med if med else 0
    z = modified_zscore(value, prices)

    above_iqr = threshold is not None and value > threshold
    above_z = z is not None and z > ZSCORE_THRESHOLD
    if not ((above_iqr or above_z) and ratio >= OUTLIER_MIN_RATIO):
        return None

    diff_pct = _pct_diff(value, med)
    severity = FindingSeverity.RELEVANTE if ratio >= 2 else FindingSeverity.ATENCAO
    confidence = round(min(0.9, 0.45 + 0.06 * comparables.sample_size), 3)

    return FindingCandidate(
        rule_code="unit_price_outlier",
        title=f"Preço unitário {diff_pct:+.0f}% acima da mediana em itens comparáveis",
        summary=(
            f"O item '{_short(item.description)}' foi homologado a "
            f"R$ {value:,.2f} por {item.unit or 'unidade'}, enquanto a mediana de "
            f"{comparables.sample_size} compras comparáveis é R$ {med:,.2f}."
        ),
        explanation=(
            "Preços unitários acima do intervalo interquartil de compras "
            "equivalentes podem indicar sobrepreço, mas também podem decorrer de "
            "especificações, frete, prazos ou condições contratuais distintas. "
            "Trata-se de indicador para verificação, não de conclusão."
        ),
        methodology=comparables.methodology,
        limitations=comparables.limitations,
        severity=severity,
        metrics={
            "unit_price": round(value, 4),
            "reference_median": round(med, 4),
            "p25": dist.p25,
            "p75": dist.p75,
            "iqr": iqr,
            "outlier_threshold": threshold,
            "modified_zscore": round(z, 3) if z is not None else None,
            "difference_pct": round(diff_pct, 2),
            "sample_size": comparables.sample_size,
            "unit": item.unit,
        },
        evidence=[
            {
                "type": "unit_price_comparison",
                "item_id": item.id,
                "item_number": item.item_number,
                "unit_price": value,
                "reference": {"median": med, "p25": dist.p25, "p75": dist.p75},
            }
        ],
        source_records=comparables.records[:25],
        confidence=confidence,
    )


def rule_total_above_estimate(procurement: Procurement) -> FindingCandidate | None:
    """Valor homologado acima do valor estimado da contratação."""
    estimated = procurement.estimated_total
    approved = procurement.approved_total
    if not estimated or not approved or estimated <= 0:
        return None
    ratio = float(approved) / float(estimated)
    if ratio < 1.1:
        return None

    return FindingCandidate(
        rule_code="total_above_estimate",
        title=f"Valor homologado {ratio * 100 - 100:.0f}% acima do estimado",
        summary=(
            f"O valor homologado (R$ {float(approved):,.2f}) supera o valor "
            f"estimado (R$ {float(estimated):,.2f}) da contratação "
            f"{procurement.pncp_control_number or ''}."
        ),
        explanation=(
            "A homologação acima do estimado merece verificação quanto a "
            "justificativas formais de acréscimo e à metodologia da estimativa. "
            "Por si só, não configura irregularidade."
        ),
        methodology=(
            "Comparação direta entre `valorTotalHomologado` e `valorTotalEstimado` "
            "publicados no PNCP, com limiar de 10%."
        ),
        limitations=(
            "O valor estimado pode ser uma referência genérica e não refletir o "
            "escopo final; acréscimos podem ser legais e fundamentados."
        ),
        severity=FindingSeverity.ATENCAO,
        metrics={
            "estimated_total": float(estimated),
            "approved_total": float(approved),
            "ratio": round(ratio, 4),
        },
        evidence=[{"type": "value_comparison", "estimated": float(estimated), "approved": float(approved)}],
        source_records=[
            {
                "pncp_control_number": procurement.pncp_control_number,
                "source_url": procurement.source_url,
            }
        ],
        confidence=0.6,
    )


def rule_quantity_inconsistent(
    item: ProcurementItem, comparables: ComparableDataset
) -> FindingCandidate | None:
    """Quantidade muito distante do padrão para o item comparável."""
    if not comparables.is_conclusive or item.quantity is None:
        return None
    quantities = [
        r["quantity"] for r in comparables.records if r.get("quantity") is not None
    ]
    if len(quantities) < MIN_SAMPLE:
        return None
    med = median(quantities)
    if not med:
        return None
    q = float(item.quantity)
    ratio = q / med
    if ratio < 10:
        return None

    return FindingCandidate(
        rule_code="quantity_inconsistent",
        title=f"Quantidade {ratio:.1f}x acima do padrão comparável",
        summary=(
            f"O item '{_short(item.description)}' possui quantidade {q:,.0f} "
            f"{item.unit or ''}, contra mediana de {med:,.0f} em compras comparáveis."
        ),
        explanation=(
            "Quantidades muito acima do padrão podem refletir demanda legítima "
            "repetida ou erro de digitação/consolidação. Requer verificação do "
            "objeto, justificativa de demanda e divisão em itens."
        ),
        methodology="Comparação de quantidade com a mediana de itens equivalentes.",
        limitations="Compras por registro de preços podem agrupar demandas de vários órgãos.",
        severity=FindingSeverity.ATENCAO,
        metrics={"quantity": q, "reference_median": med, "ratio": round(ratio, 2), "unit": item.unit},
        evidence=[{"type": "quantity_comparison", "quantity": q, "median": med}],
        source_records=comparables.records[:15],
        confidence=0.45,
    )


def rule_supplier_concentration(
    entity_name: str,
    supplier_name: str,
    supplier_total: float,
    entity_total: float,
    contract_count: int,
    period: str,
) -> FindingCandidate | None:
    """Concentração relevante de contratos em um mesmo fornecedor."""
    if entity_total <= 0:
        return None
    share = supplier_total / entity_total
    if share < 0.5 or contract_count < 3:
        return None

    return FindingCandidate(
        rule_code="supplier_concentration",
        title=f"Concentração de {share * 100:.0f}% em um fornecedor",
        summary=(
            f"O fornecedor {supplier_name} concentrou {(share * 100):.0f}% do valor "
            f"contratado por {entity_name} no período {period}, em {contract_count} contratos."
        ),
        explanation=(
            "Alta concentração pode indicar direcionamento, mas também é esperada "
            "em mercados especializados ou por continuidade de serviços. Indicador "
            "para verificação de competitividade dos certames."
        ),
        methodology="Participação do fornecedor no valor total contratado pela entidade no período.",
        limitations="Basear-se apenas no valor contratado; licitações desertas e monopólios legítimos não são distinguidos.",
        severity=FindingSeverity.ATENCAO,
        metrics={"share": round(share, 4), "supplier_total": supplier_total, "entity_total": entity_total, "contract_count": contract_count},
        evidence=[{"type": "concentration", "share": share, "contract_count": contract_count}],
        source_records=[],
        confidence=0.5,
    )


def rule_large_contract_amendment(
    contract_control: str, amendment_value: float, contract_value: float, term_number: str | None
) -> FindingCandidate | None:
    """Aditivo contratual de grande proporção."""
    if contract_value <= 0:
        return None
    ratio = amendment_value / contract_value
    if ratio < 0.25:
        return None
    return FindingCandidate(
        rule_code="large_contract_amendment",
        title=f"Aditivo de {ratio * 100:.0f}% do valor do contrato",
        summary=(
            f"O termo {term_number or ''} acrescenta R$ {amendment_value:,.2f} a um "
            f"contrato de R$ {contract_value:,.2f}."
        ),
        explanation=(
            "Acréscimos relevantes podem ser legais (dentro dos limites da Lei "
            "14.133/2021) quando justificados. A verificação deve considerar "
            "fundamentação, limites legais e alteração do objeto."
        ),
        methodology="Razão entre o valor do aditivo e o valor global do contrato.",
        limitations="Não avalia a legalidade do aditivo, apenas a magnitude.",
        severity=FindingSeverity.ATENCAO,
        metrics={"ratio": round(ratio, 4), "amendment_value": amendment_value, "contract_value": contract_value},
        evidence=[{"type": "amendment", "term": term_number, "ratio": ratio}],
        source_records=[{"contract": contract_control}],
        confidence=0.5,
    )


def _short(text: str, limit: int = 80) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1] + "…"
