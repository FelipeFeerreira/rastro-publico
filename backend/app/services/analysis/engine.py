"""Motor de auditoria: aplica regras e persiste achados reproduzíveis."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.base import utcnow
from app.models.audit import AuditFinding, AuditRule
from app.models.enums import FindingSeverity, FindingStatus
from app.models.procurement import Contract, Procurement, ProcurementItem
from app.services.analysis import rules
from app.services.analysis.reference import find_comparables

logger = get_logger(__name__)

RULE_DEFINITIONS: list[dict] = [
    {
        "code": "unit_price_outlier",
        "name": "Preço unitário fora do padrão",
        "description": (
            "Sinaliza item cujo preço unitário homologado supera o intervalo "
            "interquartil de compras comparáveis, considerando categoria e unidade."
        ),
        "severity": FindingSeverity.ATENCAO,
        "rule_type": "unit_price_outlier",
        "parameters": {"iqr_factor": 1.5, "min_ratio": 1.3, "min_sample": 5},
        "methodology": "Mediana e IQR de itens equivalentes; escore z modificado (MAD).",
    },
    {
        "code": "total_above_estimate",
        "name": "Valor homologado acima do estimado",
        "description": "Compara valor homologado com valor estimado da contratação (limiar 10%).",
        "severity": FindingSeverity.ATENCAO,
        "rule_type": "total_above_estimate",
        "parameters": {"threshold": 0.10},
        "methodology": "Razão entre valor homologado e estimado publicados no PNCP.",
    },
    {
        "code": "quantity_inconsistent",
        "name": "Quantidade inconsistente",
        "description": "Quantidade muito acima da mediana de itens comparáveis.",
        "severity": FindingSeverity.ATENCAO,
        "rule_type": "quantity_inconsistent",
        "parameters": {"min_ratio": 10},
        "methodology": "Comparação de quantidade com mediana de itens equivalentes.",
    },
    {
        "code": "supplier_concentration",
        "name": "Concentração de fornecedor",
        "description": "Concentração relevante de valor contratado em um único fornecedor.",
        "severity": FindingSeverity.ATENCAO,
        "rule_type": "supplier_concentration",
        "parameters": {"min_share": 0.5, "min_contracts": 3},
        "methodology": "Participação do fornecedor no valor contratado pela entidade no período.",
    },
    {
        "code": "large_contract_amendment",
        "name": "Aditivo contratual relevante",
        "description": "Aditivo que acrescenta parcela significativa ao valor do contrato.",
        "severity": FindingSeverity.ATENCAO,
        "rule_type": "large_contract_amendment",
        "parameters": {"min_ratio": 0.25},
        "methodology": "Razão entre valor do aditivo e valor global do contrato.",
    },
]


def ensure_rules(db: Session) -> dict[str, AuditRule]:
    """Garante que as regras existam e retorna um mapa por código."""
    rules_by_code: dict[str, AuditRule] = {}
    for definition in RULE_DEFINITIONS:
        rule = db.scalar(select(AuditRule).where(AuditRule.code == definition["code"]))
        if rule is None:
            rule = AuditRule(
                code=definition["code"],
                name=definition["name"],
                description=definition["description"],
                severity=definition["severity"],
                rule_type=definition["rule_type"],
                parameters=definition["parameters"],
                methodology=definition["methodology"],
            )
            db.add(rule)
        rules_by_code[definition["code"]] = rule
    db.flush()
    return rules_by_code


class AuditEngine:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- Persistência de achados ---
    def _persist(self, candidate: rules.FindingCandidate, **refs: int | None) -> AuditFinding:
        rule = self.db.scalar(select(AuditRule).where(AuditRule.code == candidate.rule_code))
        if rule is None:
            raise RuntimeError(f"Regra não cadastrada: {candidate.rule_code}")

        existing = self.db.scalar(
            select(AuditFinding).where(
                AuditFinding.rule_id == rule.id,
                AuditFinding.procurement_id == refs.get("procurement_id"),
                AuditFinding.title == candidate.title,
            )
        )
        if existing is not None:
            existing.summary = candidate.summary
            existing.metrics = candidate.metrics
            existing.evidence = candidate.evidence
            existing.updated_at = utcnow()
            return existing

        finding = AuditFinding(
            public_id=f"FND-{uuid.uuid4().hex[:12].upper()}",
            rule_id=rule.id,
            status=FindingStatus.IDENTIFICADO,
            severity=candidate.severity,
            title=candidate.title,
            summary=candidate.summary,
            explanation=candidate.explanation,
            methodology=candidate.methodology,
            limitations=candidate.limitations,
            metrics=candidate.metrics,
            evidence=candidate.evidence,
            source_records=candidate.source_records,
            confidence=candidate.confidence,
            review_history=[
                {
                    "at": utcnow().isoformat(),
                    "status": FindingStatus.IDENTIFICADO.value,
                    "by": "motor-de-auditoria",
                }
            ],
            entity_id=refs.get("entity_id"),
            municipality_id=refs.get("municipality_id"),
            supplier_id=refs.get("supplier_id"),
            procurement_id=refs.get("procurement_id"),
            contract_id=refs.get("contract_id"),
        )
        self.db.add(finding)
        self.db.flush()
        return finding

    # --- Avaliações ---
    def evaluate_item(self, item: ProcurementItem) -> list[AuditFinding]:
        if not item.category_key:
            return []
        procurement = item.procurement
        reference_date = procurement.published_at.date() if procurement.published_at else None
        comparables = find_comparables(
            self.db,
            category_key=item.category_key,
            unit=item.unit,
            reference_date=reference_date,
            exclude_procurement_id=procurement.id,
        )
        findings: list[AuditFinding] = []
        for candidate in (
            rules.rule_unit_price_outlier(item, comparables),
            rules.rule_quantity_inconsistent(item, comparables),
        ):
            if candidate is not None:
                findings.append(
                    self._persist(
                        candidate,
                        entity_id=procurement.entity_id,
                        municipality_id=procurement.municipality_id,
                        procurement_id=procurement.id,
                    )
                )
        return findings

    def evaluate_procurement(self, procurement: Procurement) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        candidate = rules.rule_total_above_estimate(procurement)
        if candidate is not None:
            findings.append(
                self._persist(
                    candidate,
                    entity_id=procurement.entity_id,
                    municipality_id=procurement.municipality_id,
                    procurement_id=procurement.id,
                )
            )
        for item in procurement.items:
            findings.extend(self.evaluate_item(item))
        return findings

    def evaluate_entity_concentration(
        self, entity_id: int, start: date | None = None, end: date | None = None
    ) -> AuditFinding | None:
        from app.models.geo import GovernmentEntity  # evita import circular

        entity = self.db.get(GovernmentEntity, entity_id)
        if entity is None:
            return None

        stmt = (
            select(
                Contract.supplier_id,
                func.count(Contract.id),
                func.sum(Contract.global_value),
            )
            .where(Contract.entity_id == entity_id, Contract.supplier_id.is_not(None))
            .group_by(Contract.supplier_id)
        )
        if start is not None:
            stmt = stmt.where(Contract.signed_at >= start)
        if end is not None:
            stmt = stmt.where(Contract.signed_at <= end)
        rows = self.db.execute(stmt).all()
        if not rows:
            return None

        entity_total = sum(float(total or 0) for _, _, total in rows)
        supplier_id, count, total = max(rows, key=lambda r: float(r[2] or 0))
        from app.models.supplier import Supplier

        supplier = self.db.get(Supplier, supplier_id)
        candidate = rules.rule_supplier_concentration(
            entity.name,
            supplier.name if supplier else f"fornecedor {supplier_id}",
            float(total or 0),
            entity_total,
            int(count),
            (
                f"{start.isoformat() if start else 'início'} a {end.isoformat() if end else 'hoje'}"
            ),
        )
        if candidate is None:
            return None
        return self._persist(
            candidate,
            entity_id=entity_id,
            municipality_id=entity.municipality_id,
            supplier_id=supplier_id,
        )

    def evaluate_contract_amendment(self, contract: Contract) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        base = float(contract.global_value or contract.initial_value or 0)
        for amendment in contract.amendments:
            added = float(amendment.value_added or 0)
            candidate = rules.rule_large_contract_amendment(
                contract.pncp_control_number or str(contract.id),
                added,
                base,
                amendment.term_number,
            )
            if candidate is not None:
                findings.append(
                    self._persist(
                        candidate,
                        entity_id=contract.entity_id,
                        supplier_id=contract.supplier_id,
                        contract_id=contract.id,
                    )
                )
        return findings

    def run_for_procurement_ids(self, procurement_ids: list[int]) -> int:
        ensure_rules(self.db)
        count = 0
        for pid in procurement_ids:
            procurement = self.db.get(Procurement, pid)
            if procurement is None:
                continue
            count += len(self.evaluate_procurement(procurement))
        self.db.commit()
        return count

    def run_scan(self, *, limit: int = 500, only_with_items: bool = True) -> int:
        """Varredura em lote de contratações para gerar achados."""
        ensure_rules(self.db)
        stmt = select(Procurement).order_by(Procurement.published_at.desc()).limit(limit)
        procurements = list(self.db.scalars(stmt))
        total = 0
        for procurement in procurements:
            if only_with_items and not procurement.items:
                continue
            try:
                total += len(self.evaluate_procurement(procurement))
            except Exception as exc:  # noqa: BLE001
                logger.warning("Falha na auditoria da contratação %s: %s", procurement.id, exc)
        self.db.commit()
        return total
