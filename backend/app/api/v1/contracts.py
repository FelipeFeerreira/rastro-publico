"""Contratos administrativos."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.geo import GovernmentEntity, Municipality, State
from app.models.procurement import Contract
from app.schemas.common import Page
from app.schemas.domain import ContractDetail, ContractSummary

router = APIRouter(prefix="/contratos", tags=["Contratos"])


@router.get("", response_model=Page[ContractSummary])
def list_contracts(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    uf: str | None = None,
    entity_id: int | None = None,
    supplier_id: int | None = None,
    year: int | None = None,
    uasg: str | None = Query(default=None, description="Filtra pela unidade gestora (UASG)"),
    source_system: str | None = Query(
        default=None, description="Sistema de origem: pncp | comprasnet"
    ),
    organization_code: str | None = Query(
        default=None, description="Código do órgão de origem (ex.: 26439)"
    ),
) -> Page[ContractSummary]:
    stmt = select(Contract)
    count_stmt = select(func.count()).select_from(Contract)
    filters = []
    if uasg:
        filters.append(Contract.uasg == uasg)
    if source_system:
        filters.append(Contract.source_system == source_system)
    if organization_code:
        filters.append(Contract.organization_code == organization_code)
    if uf:
        filters.append(
            Contract.entity_id.in_(
                select(GovernmentEntity.id)
                .join(Municipality, GovernmentEntity.municipality_id == Municipality.id)
                .join(State, Municipality.state_id == State.id)
                .where(State.uf == uf.upper())
            )
        )
    if entity_id:
        filters.append(Contract.entity_id == entity_id)
    if supplier_id:
        filters.append(Contract.supplier_id == supplier_id)
    if year:
        filters.append(Contract.year == year)
    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)

    total = int(db.scalar(count_stmt) or 0)
    stmt = (
        stmt.options(selectinload(Contract.supplier), selectinload(Contract.entity))
        .order_by(Contract.signed_at.desc().nullslast())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return Page.build(list(db.scalars(stmt)), total, page, page_size)


@router.get("/{contract_id}", response_model=ContractDetail)
def get_contract(contract_id: int, db: Session = Depends(get_db)) -> ContractDetail:
    contract = db.scalar(
        select(Contract)
        .options(
            selectinload(Contract.supplier),
            selectinload(Contract.entity),
            selectinload(Contract.amendments),
        )
        .where(Contract.id == contract_id)
    )
    if contract is None:
        raise HTTPException(status_code=404, detail="Contrato não encontrado.")
    detail = ContractDetail.model_validate(contract)
    if contract.source is not None:
        detail.source = contract.source  # type: ignore[assignment]
    return detail
