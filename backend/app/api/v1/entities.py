"""Órgãos/entidades, municípios e estados."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.geo import GovernmentEntity, Municipality, State
from app.models.procurement import Contract, Payment, Procurement
from app.models.source import DataSource
from app.schemas.common import Page
from app.schemas.domain import (
    CampusDashboard,
    CampusFinancials,
    CampusTotals,
    ContractSummary,
    EntitySummary,
    MunicipalityOut,
    ProcurementSummary,
    SourceOut,
    StateOut,
)

router = APIRouter(tags=["Órgãos e territórios"])


# --- Órgãos/entidades ---
@router.get("/orgaos", response_model=Page[EntitySummary])
def list_entities(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    uf: str | None = None,
    sphere: str | None = None,
    uasg: str | None = Query(default=None, description="Unidade gestora (UASG)"),
) -> Page[EntitySummary]:
    stmt = select(GovernmentEntity)
    count_stmt = select(func.count()).select_from(GovernmentEntity)
    filters = []
    if q:
        filters.append(GovernmentEntity.name.ilike(f"%{q}%"))
    if uasg:
        filters.append(GovernmentEntity.uasg == uasg)
    if uf:
        filters.append(
            GovernmentEntity.state_id.in_(select(State.id).where(State.uf == uf.upper()))
        )
    if sphere:
        filters.append(GovernmentEntity.sphere == sphere)
    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)
    total = int(db.scalar(count_stmt) or 0)
    stmt = stmt.order_by(GovernmentEntity.name).offset((page - 1) * page_size).limit(page_size)
    return Page.build(list(db.scalars(stmt)), total, page, page_size)


@router.get("/orgaos/{entity_id}", response_model=EntitySummary)
def get_entity(entity_id: int, db: Session = Depends(get_db)) -> GovernmentEntity:
    entity = db.get(GovernmentEntity, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Órgão não encontrado.")
    return entity


@router.get("/orgaos/{entity_id}/contratacoes", response_model=Page[ProcurementSummary])
def entity_procurements(
    entity_id: int,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[ProcurementSummary]:
    stmt = select(Procurement).where(Procurement.entity_id == entity_id)
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    stmt = (
        stmt.options(selectinload(Procurement.entity), selectinload(Procurement.municipality))
        .order_by(Procurement.published_at.desc().nullslast())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return Page.build(list(db.scalars(stmt)), total, page, page_size)


@router.get("/orgaos/{entity_id}/contratos", response_model=Page[ContractSummary])
def entity_contracts(
    entity_id: int,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[ContractSummary]:
    stmt = select(Contract).where(Contract.entity_id == entity_id)
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    stmt = (
        stmt.options(selectinload(Contract.supplier), selectinload(Contract.entity))
        .order_by(Contract.signed_at.desc().nullslast())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return Page.build(list(db.scalars(stmt)), total, page, page_size)


# --- Estados ---
@router.get("/estados", response_model=list[StateOut])
def list_states(db: Session = Depends(get_db)) -> list[State]:
    return list(db.scalars(select(State).order_by(State.name)))


# --- Municípios ---
@router.get("/municipios", response_model=Page[MunicipalityOut])
def list_municipalities(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    uf: str | None = None,
) -> Page[MunicipalityOut]:
    stmt = select(Municipality)
    count_stmt = select(func.count()).select_from(Municipality)
    filters = []
    if q:
        filters.append(Municipality.name.ilike(f"%{q}%"))
    if uf:
        filters.append(Municipality.state_id.in_(select(State.id).where(State.uf == uf.upper())))
    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)
    total = int(db.scalar(count_stmt) or 0)
    stmt = stmt.order_by(Municipality.name).offset((page - 1) * page_size).limit(page_size)
    return Page.build(list(db.scalars(stmt)), total, page, page_size)


@router.get("/municipios/{ibge_code}")
def get_municipality(ibge_code: str, db: Session = Depends(get_db)) -> dict:
    municipality = db.scalar(select(Municipality).where(Municipality.ibge_code == ibge_code))
    if municipality is None:
        raise HTTPException(status_code=404, detail="Município não encontrado.")
    state = db.get(State, municipality.state_id)
    procurement_count, estimated = db.execute(
        select(
            func.count(Procurement.id),
            func.coalesce(func.sum(Procurement.estimated_total), 0),
        ).where(Procurement.municipality_id == municipality.id)
    ).one()
    return {
        "id": municipality.id,
        "ibge_code": municipality.ibge_code,
        "name": municipality.name,
        "uf": state.uf if state else None,
        "state_name": state.name if state else None,
        "procurement_count": int(procurement_count or 0),
        "estimated_total": float(estimated or 0),
    }


# --- Painel de campus (por UASG) ---
@router.get("/campus/{uasg}", response_model=CampusDashboard)
def get_campus(uasg: str, db: Session = Depends(get_db)) -> CampusDashboard:
    """Resumo agregado e verificável de uma unidade gestora (campus/UASG).

    Todos os valores vêm de registros importados. Estágios financeiros são
    mantidos separados e somados apenas dentro do próprio estágio, evitando
    contagem duplicada. Contratado nunca é apresentado como pago.
    """
    entity = db.scalar(select(GovernmentEntity).where(GovernmentEntity.uasg == uasg))
    if entity is None:
        raise HTTPException(status_code=404, detail="Campus (UASG) não encontrado.")

    municipality_name = None
    uf = None
    if entity.municipality:
        municipality_name = entity.municipality.name
        state = db.get(State, entity.municipality.state_id)
        uf = state.uf if state else None

    contract_ids = select(Contract.id).where(Contract.uasg == uasg)
    row = db.execute(
        select(
            func.count(Contract.id),
            func.count(func.distinct(Contract.supplier_id)),
            func.min(Contract.signed_at),
            func.max(Contract.signed_at),
            func.max(Contract.collected_at),
            func.coalesce(func.sum(Contract.global_value), 0),
        ).where(Contract.uasg == uasg)
    ).one()
    contracts_count, suppliers_count, first_date, last_date, last_collection, contracted = row

    financials = CampusFinancials(contracted=Decimal(contracted or 0))
    stage_rows = db.execute(
        select(Payment.stage, func.coalesce(func.sum(Payment.value), 0), func.count(Payment.id))
        .where(Payment.contract_id.in_(contract_ids))
        .group_by(Payment.stage)
    ).all()
    for stage, total, count in stage_rows:
        name = stage.value if hasattr(stage, "value") else str(stage)
        financials.payment_events += int(count)
        if name == "empenhado":
            financials.committed = Decimal(total or 0)
        elif name == "liquidado":
            financials.liquidated = Decimal(total or 0)
        elif name == "pago":
            financials.paid = Decimal(total or 0)

    source = db.get(DataSource, entity.source_id) if entity.source_id else None
    notes = [
        "“Contratado” é o valor dos contratos; “pago” é o dinheiro que saiu. "
        "Contratar não é pagar.",
        "Despesa federal (IFSP). É diferente da despesa municipal da Prefeitura de "
        "Salto, que tem orçamento e portal próprios.",
    ]
    if financials.liquidated and financials.paid and financials.liquidated < financials.paid:
        notes.append(
            "O valor “liquidado” registrado na fonte pode estar subestimado em relação "
            "ao “pago”; ambos vêm dos empenhos oficiais."
        )

    return CampusDashboard(
        entity=EntitySummary.model_validate(entity),
        uasg=uasg,
        municipality_name=municipality_name,
        uf=uf,
        is_federal=entity.sphere.value == "federal",
        totals=CampusTotals(
            contracts=int(contracts_count or 0),
            suppliers=int(suppliers_count or 0),
            first_contract_date=first_date,
            last_contract_date=last_date,
            last_collection_at=last_collection,
        ),
        financials=financials,
        source=SourceOut.model_validate(source) if source else None,
        notes=notes,
    )
