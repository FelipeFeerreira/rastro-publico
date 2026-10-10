"""Painel administrativo: estatísticas, ingestão e auditoria (somente admin)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import rate_limit, require_admin
from app.db.session import SessionLocal, get_db
from app.models.audit import AuditFinding
from app.models.geo import GovernmentEntity, Municipality
from app.models.procurement import Contract, Procurement, ProcurementResult
from app.models.source import CollectionRun, DataSource
from app.models.supplier import Supplier
from app.models.user import User
from app.services.analysis.engine import AuditEngine
from app.services.ingestion import IngestionService

router = APIRouter(prefix="/admin", tags=["Administração"])


class IngestRequest(BaseModel):
    start: date
    end: date
    modality_codes: list[int] | None = None
    uf: str | None = None
    municipality_ibge: str | None = None
    cnpj: str | None = None
    with_items: bool = False
    max_pages_per_modality: int = Field(default=1, ge=1, le=50)


@router.get("/estatisticas")
def stats(db: Session = Depends(get_db), _: User = Depends(require_admin)) -> dict:
    def count(model) -> int:
        return int(db.scalar(select(func.count()).select_from(model)) or 0)

    return {
        "contratacoes": count(Procurement),
        "itens": count(ProcurementResult),
        "contratos": count(Contract),
        "fornecedores": count(Supplier),
        "orgaos": count(GovernmentEntity),
        "municipios": count(Municipality),
        "achados": count(AuditFinding),
        "fontes": count(DataSource),
        "execucoes": count(CollectionRun),
    }


@router.get("/execucoes")
def list_runs(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    limit: int = 50,
) -> list[dict]:
    runs = db.scalars(
        select(CollectionRun).order_by(CollectionRun.started_at.desc()).limit(min(limit, 200))
    )
    return [
        {
            "id": r.id,
            "source_id": r.source_id,
            "scope": r.scope,
            "status": r.status.value,
            "started_at": r.started_at.isoformat(),
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "records_fetched": r.records_fetched,
            "records_inserted": r.records_inserted,
            "records_updated": r.records_updated,
            "error_count": r.error_count,
            "message": r.message,
        }
        for r in runs
    ]


def _run_ingestion(request: IngestRequest) -> None:
    db = SessionLocal()
    try:
        IngestionService(db).ingest_pncp_publications(
            request.start,
            request.end,
            modality_codes=request.modality_codes,
            uf=request.uf,
            municipality_ibge=request.municipality_ibge,
            cnpj=request.cnpj,
            with_items=request.with_items,
            max_pages_per_modality=request.max_pages_per_modality,
        )
    finally:
        db.close()


@router.post("/ingestao/pncp", dependencies=[Depends(rate_limit(5, scope="admin_ingest"))])
def trigger_ingestion(
    payload: IngestRequest,
    background: BackgroundTasks,
    _: User = Depends(require_admin),
) -> dict:
    if payload.end < payload.start:
        raise HTTPException(status_code=422, detail="Data final anterior à inicial.")
    background.add_task(_run_ingestion, payload)
    return {
        "message": "Ingestão PNCP agendada em segundo plano.",
        "intervalo": f"{payload.start} a {payload.end}",
    }


@router.post("/auditoria/executar")
def run_audit(
    limit: int = 500, db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> dict:
    created = AuditEngine(db).run_scan(limit=limit)
    return {"message": "Varredura de auditoria concluída.", "achados": created}
