"""Despesas municipais (TCE-SP) — API somente leitura.

Registros municipais são mantidos **separados** das contratações e pagamentos
federais. Filtra por município (IBGE), período, instituição, fornecedor e estágio.
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.enums import MunicipalExpenseStage
from app.models.geo import GovernmentEntity, Municipality
from app.models.municipal import MunicipalExpense
from app.schemas.common import Page
from app.schemas.municipal import MunicipalExpenseOut, MunicipalExpenseTotals

router = APIRouter(prefix="/despesas-municipais", tags=["Despesas municipais"])

_STAGES = {s.value for s in MunicipalExpenseStage}


def _base_filters(
    municipio_ibge: str | None,
    ano: int | None,
    mes: int | None,
    entity_id: int | None,
    supplier_id: int | None,
    supplier_name: str | None,
    stage: str | None,
):
    filters = []
    if municipio_ibge:
        filters.append(
            MunicipalExpense.municipality_id.in_(
                select(Municipality.id).where(Municipality.ibge_code == municipio_ibge)
            )
        )
    if ano is not None:
        filters.append(MunicipalExpense.event_year == ano)
    if mes is not None:
        filters.append(MunicipalExpense.event_month == mes)
    if entity_id is not None:
        filters.append(MunicipalExpense.entity_id == entity_id)
    if supplier_id is not None:
        filters.append(MunicipalExpense.supplier_id == supplier_id)
    if supplier_name:
        filters.append(MunicipalExpense.supplier_name.ilike(f"%{supplier_name}%"))
    if stage:
        if stage not in _STAGES:
            raise HTTPException(status_code=422, detail="Estágio inválido.")
        filters.append(MunicipalExpense.stage == MunicipalExpenseStage(stage))
    return filters


@router.get("", response_model=Page[MunicipalExpenseOut])
def list_municipal_expenses(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    municipio_ibge: str | None = Query(default=None, description="Código IBGE (ex.: 3545209)"),
    ano: int | None = None,
    mes: int | None = Query(default=None, ge=1, le=12),
    entity_id: int | None = None,
    supplier_id: int | None = None,
    supplier_name: str | None = None,
    stage: str | None = Query(default=None, description="empenhado | liquidado | pago | reforco | anulacao"),
) -> Page[MunicipalExpenseOut]:
    filters = _base_filters(
        municipio_ibge, ano, mes, entity_id, supplier_id, supplier_name, stage
    )
    stmt = select(MunicipalExpense)
    count_stmt = select(func.count()).select_from(MunicipalExpense)
    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)

    total = int(db.scalar(count_stmt) or 0)
    stmt = (
        stmt.order_by(
            MunicipalExpense.event_year.desc().nullslast(),
            MunicipalExpense.event_month.desc().nullslast(),
            MunicipalExpense.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = list(db.scalars(stmt))

    # Nome da instituição para exibição (uma consulta em lote).
    entity_ids = [r.entity_id for r in rows if r.entity_id]
    names = {
        e.id: e.name
        for e in db.scalars(
            select(GovernmentEntity).where(GovernmentEntity.id.in_(entity_ids))
        )
    } if entity_ids else {}

    items = []
    for row in rows:
        data = MunicipalExpenseOut.model_validate(row)
        if row.entity_id:
            data.entity_name = names.get(row.entity_id)
        items.append(data)
    return Page.build(items, total, page, page_size)


@router.get("/resumo", response_model=MunicipalExpenseTotals)
def municipal_expenses_summary(
    db: Session = Depends(get_db),
    municipio_ibge: str | None = None,
    ano: int | None = None,
    mes: int | None = Query(default=None, ge=1, le=12),
    entity_id: int | None = None,
    supplier_id: int | None = None,
    supplier_name: str | None = None,
) -> MunicipalExpenseTotals:
    filters = _base_filters(
        municipio_ibge, ano, mes, entity_id, supplier_id, supplier_name, None
    )
    rows = db.execute(
        select(
            MunicipalExpense.stage,
            func.coalesce(func.sum(MunicipalExpense.value), 0),
            func.count(MunicipalExpense.id),
        )
        .where(*filters)
        .group_by(MunicipalExpense.stage)
    ).all()

    totals = MunicipalExpenseTotals()
    for stage, total, count in rows:
        name = stage.value if hasattr(stage, "value") else str(stage)
        totals.records += int(count)
        amount = Decimal(total or 0)
        if name == "empenhado":
            totals.empenhado = amount
        elif name == "liquidado":
            totals.liquidado = amount
        elif name == "pago":
            totals.pago = amount
        elif name == "reforco":
            totals.reforco = amount
        elif name == "anulacao":
            totals.anulacao = amount

    totals.committed_net = totals.empenhado + totals.reforco - totals.anulacao
    return totals
