"""Pagamentos e execução financeira (empenhado, liquidado, pago)."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.enums import FinancialStage
from app.models.procurement import Contract, Payment
from app.schemas.common import Page
from app.schemas.domain import PaymentOut, PaymentSummary

router = APIRouter(prefix="/pagamentos", tags=["Pagamentos"])

_STAGES = {s.value for s in FinancialStage}


@router.get("", response_model=Page[PaymentOut])
def list_payments(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    contract_id: int | None = None,
    entity_id: int | None = None,
    supplier_id: int | None = None,
    uasg: str | None = Query(default=None, description="Unidade gestora (UASG)"),
    stage: str | None = Query(default=None, description="empenhado | liquidado | pago"),
    year: int | None = None,
) -> Page[PaymentOut]:
    stmt = select(Payment)
    count_stmt = select(func.count()).select_from(Payment)
    filters = []
    if contract_id:
        filters.append(Payment.contract_id == contract_id)
    if entity_id:
        filters.append(Payment.entity_id == entity_id)
    if supplier_id:
        filters.append(Payment.supplier_id == supplier_id)
    if stage:
        if stage not in _STAGES:
            from fastapi import HTTPException

            raise HTTPException(status_code=422, detail="Estágio inválido.")
        filters.append(Payment.stage == FinancialStage(stage))
    if year:
        filters.append(func.extract("year", Payment.reference_date) == year)
    if uasg:
        filters.append(
            Payment.contract_id.in_(select(Contract.id).where(Contract.uasg == uasg))
        )
    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)

    total = int(db.scalar(count_stmt) or 0)
    stmt = (
        stmt.order_by(Payment.reference_date.desc().nullslast(), Payment.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return Page.build(list(db.scalars(stmt)), total, page, page_size)


def payment_summary(db: Session, contract_id: int) -> PaymentSummary:
    """Soma por estágio para um contrato (estágios mantidos separados)."""
    rows = db.execute(
        select(Payment.stage, func.coalesce(func.sum(Payment.value), 0), func.count(Payment.id))
        .where(Payment.contract_id == contract_id)
        .group_by(Payment.stage)
    ).all()
    summary = PaymentSummary()
    for stage, total, count in rows:
        stage_value = stage.value if hasattr(stage, "value") else str(stage)
        summary.count += int(count)
        if stage_value == "empenhado":
            summary.empenhado = Decimal(total or 0)
        elif stage_value == "liquidado":
            summary.liquidado = Decimal(total or 0)
        elif stage_value == "pago":
            summary.pago = Decimal(total or 0)
    return summary
