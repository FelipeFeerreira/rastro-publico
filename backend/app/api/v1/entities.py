"""Órgãos/entidades, municípios e estados."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.geo import GovernmentEntity, Municipality, State
from app.models.procurement import Contract, Procurement
from app.schemas.common import Page
from app.schemas.domain import (
    ContractSummary,
    EntitySummary,
    MunicipalityOut,
    ProcurementSummary,
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
) -> Page[EntitySummary]:
    stmt = select(GovernmentEntity)
    count_stmt = select(func.count()).select_from(GovernmentEntity)
    filters = []
    if q:
        filters.append(GovernmentEntity.name.ilike(f"%{q}%"))
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
