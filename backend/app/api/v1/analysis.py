"""Achados de auditoria e comparação de preços."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.db.base import utcnow
from app.db.session import get_db
from app.models.audit import AuditFinding
from app.models.enums import FindingSeverity, FindingStatus
from app.models.procurement import ProcurementItem
from app.models.user import User
from app.schemas.finding import ComparisonRequest, FindingOut, FindingReview
from app.services.analysis.classification import classify_price
from app.services.analysis.reference import find_comparables

logger = get_logger(__name__)

router = APIRouter(tags=["Análise e auditoria"])

VALID_STATUSES = {s.value for s in FindingStatus}


def _serialize(db: Session, finding: AuditFinding) -> dict:
    data = FindingOut.model_validate(finding).model_dump()
    data["rule_code"] = finding.rule.code if finding.rule else None
    return data


@router.get("/achados")
def list_findings(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    severity: str | None = None,
    rule_code: str | None = None,
    entity_id: int | None = None,
    procurement_id: int | None = None,
) -> dict:
    stmt = select(AuditFinding)
    count_stmt = select(func.count()).select_from(AuditFinding)
    filters = []
    if status and status in VALID_STATUSES:
        filters.append(AuditFinding.status == FindingStatus(status))
    if severity and severity in {s.value for s in FindingSeverity}:
        filters.append(AuditFinding.severity == FindingSeverity(severity))
    if entity_id:
        filters.append(AuditFinding.entity_id == entity_id)
    if procurement_id:
        filters.append(AuditFinding.procurement_id == procurement_id)
    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)

    total = int(db.scalar(count_stmt) or 0)
    stmt = (
        stmt.order_by(AuditFinding.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    findings = list(db.scalars(stmt))
    if rule_code:
        findings = [f for f in findings if f.rule and f.rule.code == rule_code]

    return {
        "items": [_serialize(db, f) for f in findings],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if page_size else 0,
        "aviso": (
            "Achados são indicadores automáticos para verificação humana. Não "
            "constituem prova ou acusação de irregularidade."
        ),
    }


@router.get("/achados/{public_id}")
def get_finding(public_id: str, db: Session = Depends(get_db)) -> dict:
    finding = db.scalar(select(AuditFinding).where(AuditFinding.public_id == public_id))
    if finding is None:
        raise HTTPException(status_code=404, detail="Achado não encontrado.")
    return _serialize(db, finding)


@router.patch("/achados/{public_id}/revisao", response_model=FindingOut)
def review_finding(
    public_id: str,
    payload: FindingReview,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    finding = db.scalar(select(AuditFinding).where(AuditFinding.public_id == public_id))
    if finding is None:
        raise HTTPException(status_code=404, detail="Achado não encontrado.")
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail="Status de revisão inválido.")

    history = list(finding.review_history or [])
    history.append(
        {
            "at": utcnow().isoformat(),
            "status": payload.status,
            "note": payload.note,
            "by": user.email,
        }
    )
    finding.status = FindingStatus(payload.status)
    finding.review_history = history
    finding.reviewed_by = user.id
    db.commit()
    db.refresh(finding)
    return _serialize(db, finding)


@router.post("/analise/comparacao")
def compare_prices(payload: ComparisonRequest, db: Session = Depends(get_db)) -> dict:
    category_key = payload.category_key
    unit = payload.unit
    reference_date = None

    target_value: float | None = None
    if payload.item_id is not None:
        item = db.get(ProcurementItem, payload.item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Item não encontrado.")
        category_key = category_key or item.category_key
        unit = unit or item.unit
        reference_date = (
            item.procurement.published_at.date() if item.procurement.published_at else None
        )
        # Valor de referência do item: menor preço homologado; senão, o estimado.
        prices = [float(r.unit_price) for r in item.results if r.unit_price is not None]
        if prices:
            target_value = min(prices)
        elif item.unit_price_estimated is not None:
            target_value = float(item.unit_price_estimated)
    if not category_key:
        raise HTTPException(
            status_code=422, detail="Informe category_key ou item_id para a comparação."
        )

    dataset = find_comparables(
        db,
        category_key=category_key,
        unit=unit,
        reference_date=reference_date,
        window_months=payload.window_months,
        state_id=payload.state_id,
    )
    classification = classify_price(target_value, dataset)
    return {
        "classification": classification.to_dict(),
        "compared_value": target_value,
        "category_key": dataset.category_key,
        "unit": dataset.unit,
        "sample_size": dataset.sample_size,
        "conclusive": dataset.is_conclusive,
        "distribution": {
            "count": dataset.distribution.count,
            "median": dataset.distribution.median,
            "p25": dataset.distribution.p25,
            "p75": dataset.distribution.p75,
            "iqr": dataset.distribution.iqr,
            "min": dataset.distribution.minimum,
            "max": dataset.distribution.maximum,
        },
        "methodology": dataset.methodology,
        "limitations": dataset.limitations,
        "records": dataset.records,
    }
