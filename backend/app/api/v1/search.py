"""Busca universal e autocomplete."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import rate_limit
from app.core.config import settings
from app.db.session import get_db
from app.schemas.assistant import SuggestionOut
from app.services.search import SearchService

router = APIRouter(tags=["Busca"])


@router.get("/search")
def search(
    request: Request,
    q: str = Query(default="", description="Termo de busca em linguagem natural"),
    types: str | None = Query(default=None, description="Tipos separados por vírgula"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    uf: str | None = None,
    year: int | None = None,
    modality: int | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(settings.rate_limit_search_per_minute, scope="search")),
) -> dict:
    service = SearchService(db)
    selected = [t.strip() for t in types.split(",")] if types else None
    response = service.search(
        q,
        types=selected,
        page=page,
        page_size=page_size,
        uf=uf,
        year=year,
        modality=modality,
        min_value=Decimal(str(min_value)) if min_value is not None else None,
        max_value=Decimal(str(max_value)) if max_value is not None else None,
    )
    return response.to_dict()


@router.get("/search/suggest", response_model=list[SuggestionOut])
def suggest(
    q: str = Query(min_length=1),
    limit: int = Query(default=8, ge=1, le=20),
    db: Session = Depends(get_db),
) -> list[dict]:
    return SearchService(db).suggest(q, limit)
