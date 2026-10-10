"""Espaço de investigação: casos, evidências e relatórios."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.enums import EvidenceKind, InvestigationStatus
from app.models.investigation import Investigation, InvestigationEvidence
from app.models.user import User
from app.schemas.finding import (
    EvidenceCreate,
    EvidenceOut,
    InvestigationCreate,
    InvestigationDetail,
    InvestigationOut,
    InvestigationUpdate,
)
from app.services.reporting import build_report, render_pdf

router = APIRouter(prefix="/investigacoes", tags=["Investigações"])


def _owned(db: Session, public_id: str, user: User) -> Investigation:
    investigation = db.scalar(
        select(Investigation).where(Investigation.public_id == public_id)
    )
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigação não encontrada.")
    if investigation.owner_user_id != user.id:
        raise HTTPException(status_code=403, detail="Acesso negado a esta investigação.")
    return investigation


@router.post("", response_model=InvestigationOut, status_code=status.HTTP_201_CREATED)
def create_investigation(
    payload: InvestigationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Investigation:
    investigation = Investigation(
        public_id=f"INV-{uuid.uuid4().hex[:12].upper()}",
        owner_user_id=user.id,
        title=payload.title,
        description=payload.description,
        tags=payload.tags,
        scope=payload.scope,
    )
    db.add(investigation)
    db.commit()
    db.refresh(investigation)
    return investigation


@router.get("", response_model=list[InvestigationOut])
def list_investigations(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Investigation]:
    return list(
        db.scalars(
            select(Investigation)
            .where(Investigation.owner_user_id == user.id)
            .order_by(Investigation.created_at.desc())
        )
    )


@router.get("/{public_id}", response_model=InvestigationDetail)
def get_investigation(
    public_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Investigation:
    return _owned(db, public_id, user)


@router.patch("/{public_id}", response_model=InvestigationOut)
def update_investigation(
    public_id: str,
    payload: InvestigationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Investigation:
    investigation = _owned(db, public_id, user)
    if payload.title is not None:
        investigation.title = payload.title
    if payload.description is not None:
        investigation.description = payload.description
    if payload.tags is not None:
        investigation.tags = payload.tags
    if payload.scope is not None:
        investigation.scope = payload.scope
    if payload.status is not None:
        if payload.status not in {s.value for s in InvestigationStatus}:
            raise HTTPException(status_code=422, detail="Status inválido.")
        investigation.status = InvestigationStatus(payload.status)
    db.commit()
    db.refresh(investigation)
    return investigation


@router.delete("/{public_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_investigation(
    public_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    investigation = _owned(db, public_id, user)
    db.delete(investigation)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{public_id}/evidencias",
    response_model=EvidenceOut,
    status_code=status.HTTP_201_CREATED,
)
def add_evidence(
    public_id: str,
    payload: EvidenceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InvestigationEvidence:
    investigation = _owned(db, public_id, user)
    if payload.kind not in {k.value for k in EvidenceKind}:
        raise HTTPException(status_code=422, detail="Tipo de evidência inválido.")
    evidence = InvestigationEvidence(
        investigation_id=investigation.id,
        kind=EvidenceKind(payload.kind),
        title=payload.title,
        note=payload.note,
        reference_type=payload.reference_type,
        reference_id=payload.reference_id,
        source_url=payload.source_url,
        payload=payload.payload,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)
    return evidence


@router.delete(
    "/{public_id}/evidencias/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_evidence(
    public_id: str,
    evidence_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Response:
    investigation = _owned(db, public_id, user)
    evidence = db.get(InvestigationEvidence, evidence_id)
    if evidence is None or evidence.investigation_id != investigation.id:
        raise HTTPException(status_code=404, detail="Evidência não encontrada.")
    db.delete(evidence)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{public_id}/relatorio")
def get_report(
    public_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    investigation = _owned(db, public_id, user)
    return build_report(db, investigation)


@router.get("/{public_id}/relatorio.pdf")
def get_report_pdf(
    public_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    investigation = _owned(db, public_id, user)
    pdf = render_pdf(build_report(db, investigation))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="relatorio-{investigation.public_id}.pdf"'
        },
    )
