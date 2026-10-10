"""Contratações públicas."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.geo import Municipality, State
from app.models.procurement import Procurement
from app.schemas.common import Page
from app.schemas.domain import ProcurementDetail, ProcurementSummary

router = APIRouter(prefix="/contratacoes", tags=["Contratações"])


def _summary(p: Procurement) -> ProcurementSummary:
    return ProcurementSummary.model_validate(p)


@router.get("", response_model=Page[ProcurementSummary])
def list_procurements(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    uf: str | None = None,
    municipality_ibge: str | None = None,
    entity_id: int | None = None,
    year: int | None = None,
    modality: int | None = None,
) -> Page[ProcurementSummary]:
    stmt = select(Procurement)
    count_stmt = select(func.count()).select_from(Procurement)

    filters = []
    if municipality_ibge:
        filters.append(
            Procurement.municipality_id
            == select(Municipality.id).where(Municipality.ibge_code == municipality_ibge).scalar_subquery()
        )
    if uf:
        filters.append(
            Procurement.municipality_id.in_(
                select(Municipality.id).join(State, Municipality.state_id == State.id).where(State.uf == uf.upper())
            )
        )
    if entity_id:
        filters.append(Procurement.entity_id == entity_id)
    if year:
        filters.append(Procurement.year == year)
    if modality:
        filters.append(Procurement.modality == str(modality))

    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)

    total = int(db.scalar(count_stmt) or 0)
    stmt = (
        stmt.options(selectinload(Procurement.entity), selectinload(Procurement.municipality))
        .order_by(Procurement.published_at.desc().nullslast())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_summary(p) for p in db.scalars(stmt)]
    return Page.build(items, total, page, page_size)


@router.get("/{procurement_id}", response_model=ProcurementDetail)
def get_procurement(procurement_id: int, db: Session = Depends(get_db)) -> ProcurementDetail:
    procurement = db.scalar(
        select(Procurement)
        .options(
            selectinload(Procurement.entity),
            selectinload(Procurement.municipality),
            selectinload(Procurement.items),
        )
        .where(Procurement.id == procurement_id)
    )
    if procurement is None:
        raise HTTPException(status_code=404, detail="Contratação não encontrada.")

    detail = ProcurementDetail.model_validate(procurement)
    detail.items = procurement.items  # type: ignore[assignment]
    # Resultados homologados achatados para a interface.
    results = []
    for item in procurement.items:
        results.extend(item.results)
    detail.results = results  # type: ignore[assignment]
    if procurement.source is not None:
        detail.source = procurement.source  # type: ignore[assignment]
    return detail
