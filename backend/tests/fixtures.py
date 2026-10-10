"""Conjuntos de dados realistas e rotulados para testes (não são dados reais)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.geo import GovernmentEntity, Municipality, State
from app.models.procurement import Procurement, ProcurementItem, ProcurementResult
from app.models.supplier import Supplier
from app.services import normalization as norm


def get_or_create_campinas(db: Session) -> tuple[State, Municipality, GovernmentEntity]:
    state = db.scalar(select(State).where(State.uf == "SP"))
    if state is None:
        state = State(ibge_code="35", uf="SP", name="São Paulo")
        db.add(state)
        db.flush()
    muni = db.scalar(select(Municipality).where(Municipality.ibge_code == "3509502"))
    if muni is None:
        muni = Municipality(
            ibge_code="3509502",
            name="Campinas",
            state_id=state.id,
            search_text=norm.build_search_text("Campinas", "São Paulo"),
        )
        db.add(muni)
        db.flush()
    entity = db.scalar(select(GovernmentEntity).where(GovernmentEntity.cnpj == "51662092000100"))
    if entity is None:
        entity = GovernmentEntity(
            cnpj="51662092000100",
            name="Prefeitura Municipal de Campinas",
            acronym="PMC",
            sphere="municipal",
            power="executive",
            state_id=state.id,
            municipality_id=muni.id,
            search_text=norm.build_search_text("Prefeitura Municipal de Campinas"),
        )
        db.add(entity)
        db.flush()
    return state, muni, entity


def create_computer_dataset(db: Session) -> dict:
    """Seis compras de computadores; uma com preço unitário claramente atípico."""
    state, muni, entity = get_or_create_campinas(db)
    from app.models.source import DataSource

    data_source = db.scalar(select(DataSource).where(DataSource.code == "pncp"))
    supplier = db.scalar(select(Supplier).where(Supplier.document == "11122233000144"))
    if supplier is None:
        supplier = Supplier(
            document="11122233000144",
            document_type="PJ",
            name="TecnoInfo Equipamentos LTDA",
            search_text=norm.build_search_text("TecnoInfo Equipamentos LTDA"),
        )
        db.add(supplier)
        db.flush()

    normal_prices = [3000.0, 3100.0, 3200.0, 3300.0, 3400.0]
    created_ids: list[int] = []
    outlier_id: int | None = None

    for index, price in enumerate([*normal_prices, 12000.0]):
        control = f"51662092000100-1-{index + 1:06d}/2026"
        existing = db.scalar(
            select(Procurement).where(Procurement.pncp_control_number == control)
        )
        if existing is not None:
            created_ids.append(existing.id)
            if price == 12000.0:
                outlier_id = existing.id
            continue

        procurement = Procurement(
            source_id=data_source.id,
            entity_id=entity.id,
            municipality_id=muni.id,
            pncp_control_number=f"51662092000100-1-{index + 1:06d}/2026",
            year=2026,
            sequential=index + 1,
            number=str(100 + index),
            modality="6",
            modality_name="Dispensa",
            status="divulgada",
            status_name="Divulgada no PNCP",
            object_description="AQUISIÇÃO DE COMPUTADORES DESKTOP PARA ESCOLAS MUNICIPAIS",
            estimated_total=Decimal(str(price * 10)),
            approved_total=Decimal(str(price * 10)),
            published_at=datetime(2026, 1, 15 + index, tzinfo=UTC),
            source_url=f"https://pncp.gov.br/app/editais/51662092000100/2026/{index + 1}",
            search_text=norm.build_search_text(
                "AQUISIÇÃO DE COMPUTADORES DESKTOP", "Campinas", "Dispensa"
            ),
        )
        db.add(procurement)
        db.flush()

        item = ProcurementItem(
            procurement_id=procurement.id,
            item_number=1,
            description="COMPUTADOR DESKTOP CORE I5 8GB SSD 256GB",
            kind="material",
            unit="Unidade",
            quantity=Decimal("10"),
            unit_price_estimated=Decimal(str(price)),
            total_estimated=Decimal(str(price * 10)),
            category_key="heur:informatica",
            search_text=norm.build_search_text("COMPUTADOR DESKTOP", "Unidade"),
        )
        db.add(item)
        db.flush()

        result = ProcurementResult(
            procurement_id=procurement.id,
            item_id=item.id,
            supplier_id=supplier.id,
            result_sequential=1,
            supplier_document=supplier.document,
            supplier_name=supplier.name,
            unit_price=Decimal(str(price)),
            quantity=Decimal("10"),
            total_price=Decimal(str(price * 10)),
            source_url=procurement.source_url,
        )
        db.add(result)
        created_ids.append(procurement.id)
        if price == 12000.0:
            outlier_id = procurement.id

    db.commit()
    return {
        "state": state,
        "municipality": muni,
        "entity": entity,
        "supplier": supplier,
        "procurement_ids": created_ids,
        "outlier_id": outlier_id,
    }
