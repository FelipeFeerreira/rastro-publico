from sqlalchemy import select

from app.models.audit import AuditFinding
from app.models.procurement import Procurement
from app.services.analysis.engine import AuditEngine, ensure_rules
from app.services.analysis.reference import find_comparables
from tests.fixtures import create_computer_dataset


def test_comparables_build_robust_distribution(db):
    create_computer_dataset(db)
    dataset = find_comparables(
        db, category_key="heur:informatica", unit="Unidade", reference_date=None
    )
    assert dataset.sample_size == 6
    assert dataset.distribution.median == 3250.0
    assert dataset.is_conclusive


def test_unit_price_outlier_rule_creates_finding(db):
    data = create_computer_dataset(db)
    ensure_rules(db)
    engine = AuditEngine(db)
    procurement = db.get(Procurement, data["outlier_id"])
    findings = engine.evaluate_procurement(procurement)
    codes = {f.rule.code for f in findings}
    assert "unit_price_outlier" in codes

    finding = db.scalar(
        select(AuditFinding).where(AuditFinding.rule.has(code="unit_price_outlier"))
    )
    assert finding is not None
    assert finding.metrics["sample_size"] >= 5
    assert finding.metrics["unit_price"] == 12000.0
    assert finding.status.value == "identificado"


def test_no_finding_when_sample_is_small(db):
    """Poucos comparáveis => não sinalizar (evitar falso positivo)."""
    from decimal import Decimal

    from app.models.procurement import ProcurementItem, ProcurementResult
    from app.models.source import DataSource
    from app.services import normalization as norm
    from tests.fixtures import get_or_create_campinas

    _, muni, entity = get_or_create_campinas(db)
    source = db.scalar(select(DataSource).where(DataSource.code == "pncp"))
    procurement = Procurement(
        source_id=source.id,
        entity_id=entity.id,
        municipality_id=muni.id,
        pncp_control_number="51662092000100-1-999999/2026",
        year=2026,
        sequential=999999,
        object_description="COMPUTADOR DESKTOP ISOLADO",
        modality="6",
        search_text=norm.build_search_text("COMPUTADOR DESKTOP"),
    )
    db.add(procurement)
    db.flush()
    item = ProcurementItem(
        procurement_id=procurement.id,
        item_number=1,
        description="COMPUTADOR DESKTOP ISOLADO",
        kind="material",
        unit="Unidade",
        quantity=Decimal("1"),
        unit_price_estimated=Decimal("99999"),
        category_key="heur:informatica_isolado",
        search_text=norm.build_search_text("COMPUTADOR DESKTOP"),
    )
    db.add(item)
    db.flush()
    db.add(
        ProcurementResult(
            procurement_id=procurement.id,
            item_id=item.id,
            result_sequential=1,
            unit_price=Decimal("99999"),
            quantity=Decimal("1"),
        )
    )
    db.commit()

    findings = AuditEngine(db).evaluate_procurement(procurement)
    assert all(f.rule.code != "unit_price_outlier" for f in findings)
