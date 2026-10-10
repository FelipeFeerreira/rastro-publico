"""Fornecedores e empresas."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models.audit import AuditFinding
from app.models.procurement import Contract, ProcurementResult
from app.models.supplier import Supplier
from app.schemas.common import Page
from app.schemas.domain import ContractSummary, SupplierDetail, SupplierSummary
from app.schemas.finding import FindingOut

router = APIRouter(prefix="/fornecedores", tags=["Fornecedores"])


@router.get("", response_model=Page[SupplierSummary])
def list_suppliers(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    document: str | None = None,
) -> Page[SupplierSummary]:
    stmt = select(Supplier)
    count_stmt = select(func.count()).select_from(Supplier)
    filters = []
    if q:
        filters.append(or_(Supplier.name.ilike(f"%{q}%"), Supplier.search_text.ilike(f"%{q.lower()}%")))
    if document:
        filters.append(Supplier.document == document)
    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)
    total = int(db.scalar(count_stmt) or 0)
    stmt = stmt.order_by(Supplier.name).offset((page - 1) * page_size).limit(page_size)
    return Page.build(list(db.scalars(stmt)), total, page, page_size)


@router.get("/{supplier_id}", response_model=SupplierDetail)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)) -> SupplierDetail:
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")

    contract_count, total_value = db.execute(
        select(func.count(Contract.id), func.coalesce(func.sum(Contract.global_value), 0)).where(
            Contract.supplier_id == supplier_id
        )
    ).one()
    procurement_count = int(
        db.scalar(
            select(func.count(func.distinct(ProcurementResult.procurement_id))).where(
                ProcurementResult.supplier_id == supplier_id
            )
        )
        or 0
    )
    detail = SupplierDetail.model_validate(supplier)
    detail.contract_count = int(contract_count or 0)
    detail.total_contract_value = Decimal(total_value or 0)
    detail.procurement_count = procurement_count
    return detail


@router.get("/{supplier_id}/contratos", response_model=Page[ContractSummary])
def supplier_contracts(
    supplier_id: int,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[ContractSummary]:
    stmt = select(Contract).where(Contract.supplier_id == supplier_id)
    total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    stmt = (
        stmt.options(selectinload(Contract.supplier), selectinload(Contract.entity))
        .order_by(Contract.signed_at.desc().nullslast())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return Page.build(list(db.scalars(stmt)), total, page, page_size)


@router.get("/{supplier_id}/achados", response_model=list[FindingOut])
def supplier_findings(supplier_id: int, db: Session = Depends(get_db)) -> list[dict]:
    findings = db.scalars(
        select(AuditFinding)
        .where(AuditFinding.supplier_id == supplier_id)
        .order_by(AuditFinding.created_at.desc())
        .limit(100)
    )
    return [_with_rule(db, f) for f in findings]


def _with_rule(db: Session, finding: AuditFinding) -> dict:
    data = FindingOut.model_validate(finding).model_dump()
    data["rule_code"] = finding.rule.code if finding.rule else None
    return data
