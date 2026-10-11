"""Servidores públicos e remunerações (quando legalmente e tecnicamente disponíveis)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.geo import GovernmentEntity
from app.models.person import PublicPerson, Remuneration
from app.schemas.common import Page
from app.schemas.person import PersonDetail, PersonOut, SourceAvailability

router = APIRouter(tags=["Servidores e remuneração"])


def _attach_latest_remuneration(db: Session, persons: list[PublicPerson]) -> list[PersonOut]:
    if not persons:
        return []
    ids = [p.id for p in persons]
    rows = db.scalars(
        select(Remuneration)
        .where(Remuneration.person_id.in_(ids))
        .order_by(Remuneration.reference_year.desc().nullslast(), Remuneration.reference_month.desc().nullslast())
    )
    latest: dict[int, Remuneration] = {}
    for rem in rows:
        latest.setdefault(rem.person_id, rem)

    entity_ids = [p.entity_id for p in persons if p.entity_id]
    entities = {
        e.id: e.name
        for e in db.scalars(select(GovernmentEntity).where(GovernmentEntity.id.in_(entity_ids)))
    } if entity_ids else {}

    result = []
    for person in persons:
        data = PersonOut.model_validate(person)
        if person.entity_id:
            data.entity_name = entities.get(person.entity_id)
        rem = latest.get(person.id)
        if rem is not None:
            data.latest_gross = rem.gross_amount
            data.latest_net = rem.net_amount
            data.latest_reference_year = rem.reference_year
            data.latest_reference_month = rem.reference_month
        result.append(data)
    return result


@router.get("/servidores", response_model=Page[PersonOut])
def list_servidores(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    entity_id: int | None = None,
    uasg: str | None = Query(default=None, description="Unidade gestora (UASG)"),
    year: int | None = None,
) -> Page[PersonOut]:
    stmt = select(PublicPerson)
    count_stmt = select(func.count()).select_from(PublicPerson)
    filters = []
    if q:
        filters.append(PublicPerson.name.ilike(f"%{q}%"))
    if entity_id:
        filters.append(PublicPerson.entity_id == entity_id)
    if uasg:
        filters.append(
            PublicPerson.entity_id.in_(
                select(GovernmentEntity.id).where(GovernmentEntity.uasg == uasg)
            )
        )
    if year:
        filters.append(
            PublicPerson.id.in_(select(Remuneration.person_id).where(Remuneration.reference_year == year))
        )
    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)

    total = int(db.scalar(count_stmt) or 0)
    stmt = stmt.order_by(PublicPerson.name).offset((page - 1) * page_size).limit(page_size)
    persons = list(db.scalars(stmt))
    return Page.build(_attach_latest_remuneration(db, persons), total, page, page_size)


@router.get("/servidores/{person_id}", response_model=PersonDetail)
def get_servidor(person_id: int, db: Session = Depends(get_db)) -> PersonDetail:
    person = db.get(PublicPerson, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Servidor não encontrado.")
    detail = PersonDetail.model_validate(person)
    if person.entity_id:
        entity = db.get(GovernmentEntity, person.entity_id)
        detail.entity_name = entity.name if entity else None
    detail.remunerations = list(  # type: ignore[assignment]
        db.scalars(
            select(Remuneration)
            .where(Remuneration.person_id == person_id)
            .order_by(Remuneration.reference_year.desc().nullslast(), Remuneration.reference_month.desc().nullslast())
        )
    )
    return detail


@router.get("/salarios/fontes", response_model=list[SourceAvailability])
def salary_sources() -> list[dict]:
    """Transparência explícita sobre disponibilidade de dados de remuneração."""
    return [
        {
            "code": "transparencia",
            "name": "Portal da Transparência Federal (servidores e remuneração)",
            "status": "disponivel_com_credencial" if settings.transparencia_api_key else "credencial_ausente",
            "supports_salary": True,
            "credentials_required": True,
            "credentials_present": bool(settings.transparencia_api_key),
            "note": (
                "Cobre servidores federais (ex.: IFSP 26439). A chave gratuita "
                "TRANSPARENCIA_API_KEY é obrigatória."
            ),
        },
        {
            "code": "ifsp_dados_abertos",
            "name": "Dados Abertos do IFSP (CKAN)",
            "status": "bloqueado_waf",
            "supports_salary": False,
            "credentials_required": False,
            "credentials_present": False,
            "note": (
                "Publica a relação de servidores por campus (nome/cargo), sem valores "
                "de remuneração. O endpoint respondeu HTTP 202 vazio (proteção/WAF) "
                "durante a verificação."
            ),
        },
        {
            "code": "salto_prescon",
            "name": "Prefeitura de Salto — Remuneração (Prescon/APEX)",
            "status": "indisponivel",
            "supports_salary": True,
            "credentials_required": False,
            "credentials_present": False,
            "note": (
                "Portal Oracle APEX em saltotransparencia.presconinformatica.com.br:8443 "
                "não acessível programaticamente (porta bloqueada na verificação)."
            ),
        },
    ]
