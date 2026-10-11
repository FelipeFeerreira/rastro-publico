"""Contratos administrativos."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.v1.payments import payment_summary
from app.db.session import get_db
from app.models.enums import FinancialStage
from app.models.geo import GovernmentEntity, Municipality, State
from app.models.procurement import Contract, Payment
from app.models.supplier import Supplier
from app.schemas.common import Page
from app.schemas.domain import ContractDetail, ContractSummary, PaymentOut

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
    q: str | None = Query(default=None, description="Busca no objeto do contrato"),
    supplier_name: str | None = Query(default=None, description="Busca pelo nome do fornecedor"),
    date_from: date | None = Query(default=None, description="Assinatura a partir de"),
    date_to: date | None = Query(default=None, description="Assinatura até"),
    min_value: Decimal | None = Query(default=None, description="Valor contratado mínimo"),
    max_value: Decimal | None = Query(default=None, description="Valor contratado máximo"),
    order: str = Query(default="date_desc", description="date_desc | date_asc | value_desc | value_asc"),
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
    if q:
        filters.append(Contract.object_description.ilike(f"%{q}%"))
    if supplier_name:
        filters.append(
            Contract.supplier_id.in_(
                select(Supplier.id).where(Supplier.name.ilike(f"%{supplier_name}%"))
            )
        )
    if date_from:
        filters.append(Contract.signed_at >= date_from)
    if date_to:
        filters.append(Contract.signed_at <= date_to)
    if min_value is not None:
        filters.append(Contract.global_value >= min_value)
    if max_value is not None:
        filters.append(Contract.global_value <= max_value)
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
    ordering = {
        "date_asc": Contract.signed_at.asc().nullslast(),
        "value_desc": Contract.global_value.desc().nullslast(),
        "value_asc": Contract.global_value.asc().nullslast(),
    }.get(order, Contract.signed_at.desc().nullslast())
    stmt = (
        stmt.options(selectinload(Contract.supplier), selectinload(Contract.entity))
        .order_by(ordering)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    contracts = list(db.scalars(stmt))

    # Valor efetivamente PAGO por contrato (para não confundir com o contratado).
    paid_by_contract: dict[int, Decimal] = {}
    if contracts:
        ids = [c.id for c in contracts]
        rows = db.execute(
            select(Payment.contract_id, func.coalesce(func.sum(Payment.value), 0))
            .where(Payment.contract_id.in_(ids), Payment.stage == FinancialStage.PAGO)
            .group_by(Payment.contract_id)
        ).all()
        paid_by_contract = {int(cid): Decimal(total or 0) for cid, total in rows if cid is not None}

    items = []
    for contract in contracts:
        data = ContractSummary.model_validate(contract)
        data.paid_value = paid_by_contract.get(contract.id)
        items.append(data)
    return Page.build(items, total, page, page_size)


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
    detail.payment_summary = payment_summary(db, contract.id)
    if contract.source is not None:
        detail.source = contract.source  # type: ignore[assignment]
    return detail


@router.get("/{contract_id}/pagamentos", response_model=list[PaymentOut])
def contract_payments(
    contract_id: int, db: Session = Depends(get_db)
) -> list[dict]:
    """Lançamentos de execução (empenhado, liquidado, pago) de um contrato."""
    payments = db.scalars(
        select(Payment)
        .where(Payment.contract_id == contract_id)
        .order_by(Payment.reference_date.desc().nullslast(), Payment.id.desc())
        .limit(200)
    )
    return [PaymentOut.model_validate(p).model_dump() for p in payments]
