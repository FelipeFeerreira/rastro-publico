"""Fontes de dados oficiais e status de sincronização."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.source import CollectionRun, DataSource
from app.schemas.domain import CollectionRunOut, SourceOut

router = APIRouter(prefix="/sources", tags=["Fontes de dados"])


@router.get("", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db)) -> list[DataSource]:
    return list(db.scalars(select(DataSource).order_by(DataSource.name)))


@router.get("/{code}", response_model=SourceOut)
def get_source(code: str, db: Session = Depends(get_db)) -> DataSource:
    source = db.scalar(select(DataSource).where(DataSource.code == code))
    if source is None:
        raise HTTPException(status_code=404, detail="Fonte não encontrada.")
    return source


@router.get("/{code}/runs", response_model=list[CollectionRunOut])
def list_runs(code: str, limit: int = 20, db: Session = Depends(get_db)) -> list[CollectionRun]:
    source = db.scalar(select(DataSource).where(DataSource.code == code))
    if source is None:
        raise HTTPException(status_code=404, detail="Fonte não encontrada.")
    stmt = (
        select(CollectionRun)
        .where(CollectionRun.source_id == source.id)
        .order_by(CollectionRun.started_at.desc())
        .limit(min(limit, 100))
    )
    return list(db.scalars(stmt))
