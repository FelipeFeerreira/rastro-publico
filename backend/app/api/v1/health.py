"""Endpoints de saúde e metadados da plataforma."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import __version__
from app.core.config import settings
from app.db.session import get_db
from app.models.procurement import Contract, Procurement, ProcurementResult
from app.models.supplier import Supplier

router = APIRouter(tags=["Sistema"])


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": __version__,
        "environment": settings.environment,
        "ai_enabled": settings.ai_enabled,
    }


@router.get("/meta/coverage")
def coverage(db: Session = Depends(get_db)) -> dict:
    """Resumo do que já está disponível localmente (transparência de cobertura)."""
    return {
        "contratacoes": int(db.scalar(select(func.count()).select_from(Procurement)) or 0),
        "contratos": int(db.scalar(select(func.count()).select_from(Contract)) or 0),
        "fornecedores": int(db.scalar(select(func.count()).select_from(Supplier)) or 0),
        "resultados_preco": int(db.scalar(select(func.count()).select_from(ProcurementResult)) or 0),
        "aviso": (
            "A plataforma é independente e não constitui serviço oficial. Os dados "
            "provêm de fontes públicas oficiais e podem estar desatualizados."
        ),
    }
