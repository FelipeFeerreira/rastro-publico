"""Busca unificada sobre entidades, fornecedores, contratações e contratos.

Usa full-text search nativo do PostgreSQL (`portuguese`) com ranking, e faz
fallback para `LIKE` em bancos sem FTS (ex.: SQLite em testes). Sempre retorna
totais explícitos e agrupa resultados por tipo.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models.geo import GovernmentEntity, Municipality, State
from app.models.procurement import Contract, Procurement, ProcurementItem
from app.models.supplier import Supplier
from app.services import normalization as norm

IS_POSTGRES = engine.dialect.name == "postgresql"

RESULT_TYPES = ("procurement", "contract", "supplier", "entity", "municipality", "item")


@dataclass
class SearchHit:
    type: str
    id: int
    title: str
    subtitle: str | None = None
    description: str | None = None
    value: str | None = None
    date: str | None = None
    location: str | None = None
    url: str | None = None
    source_url: str | None = None
    score: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SearchGroup:
    type: str
    label: str
    total: int
    items: list[SearchHit]


@dataclass
class SearchResponse:
    query: str
    total: int
    page: int
    page_size: int
    groups: list[SearchGroup]
    took_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "took_ms": self.took_ms,
            "groups": [
                {
                    "type": g.type,
                    "label": g.label,
                    "total": g.total,
                    "items": [i.to_dict() for i in g.items],
                }
                for g in self.groups
            ],
        }


_TYPE_LABELS = {
    "procurement": "Contratações",
    "contract": "Contratos",
    "supplier": "Fornecedores",
    "entity": "Órgãos e entidades",
    "municipality": "Municípios",
    "item": "Itens de contratação",
}


def _fts_filter(column, query: str):
    """Cláusula de busca: FTS no Postgres, LIKE (por termo) no restante."""
    if IS_POSTGRES:
        vector = func.to_tsvector("portuguese", func.coalesce(column, ""))
        tsquery = func.plainto_tsquery("portuguese", query)
        return vector.op("@@")(tsquery)
    tokens = [t for t in norm.normalize_text(query).split() if len(t) > 2] or [
        norm.normalize_text(query)
    ]
    return or_(*[column.ilike(f"%{token}%") for token in tokens])


def _fts_rank(column, query: str) -> Any:
    if IS_POSTGRES:
        vector = func.to_tsvector("portuguese", func.coalesce(column, ""))
        tsquery = func.plainto_tsquery("portuguese", query)
        return func.ts_rank(vector, tsquery)
    return func.length(func.coalesce(column, ""))


class SearchService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # --- contagens por tipo para a página de resultados ---
    def _count(self, stmt: Select) -> int:
        return int(self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)

    def search(
        self,
        query: str,
        *,
        types: list[str] | None = None,
        page: int = 1,
        page_size: int = 10,
        uf: str | None = None,
        year: int | None = None,
        modality: int | None = None,
        min_value: Decimal | None = None,
        max_value: Decimal | None = None,
    ) -> SearchResponse:
        import time

        started = time.perf_counter()
        query = (query or "").strip()
        selected = types or list(RESULT_TYPES)
        groups: list[SearchGroup] = []
        total = 0

        if not query:
            return SearchResponse(query=query, total=0, page=page, page_size=page_size, groups=[])

        if "procurement" in selected:
            hits, count = self._search_procurements(query, page, page_size, uf, year, modality, min_value, max_value)
            groups.append(SearchGroup("procurement", _TYPE_LABELS["procurement"], count, hits))
            total += count
        if "contract" in selected:
            hits, count = self._search_contracts(query, page, page_size, uf, year)
            groups.append(SearchGroup("contract", _TYPE_LABELS["contract"], count, hits))
            total += count
        if "supplier" in selected:
            hits, count = self._search_suppliers(query, page, page_size)
            groups.append(SearchGroup("supplier", _TYPE_LABELS["supplier"], count, hits))
            total += count
        if "entity" in selected:
            hits, count = self._search_entities(query, page, page_size, uf)
            groups.append(SearchGroup("entity", _TYPE_LABELS["entity"], count, hits))
            total += count
        if "municipality" in selected:
            hits, count = self._search_municipalities(query, page, page_size, uf)
            groups.append(SearchGroup("municipality", _TYPE_LABELS["municipality"], count, hits))
            total += count
        if "item" in selected:
            hits, count = self._search_items(query, page, page_size)
            groups.append(SearchGroup("item", _TYPE_LABELS["item"], count, hits))
            total += count

        return SearchResponse(
            query=query,
            total=total,
            page=page,
            page_size=page_size,
            groups=[g for g in groups if g.items],
            took_ms=round((time.perf_counter() - started) * 1000, 2),
        )

    # --- busca por tipo ---
    def _search_procurements(self, q, page, page_size, uf, year, modality, min_value, max_value):
        stmt = select(Procurement).where(_fts_filter(Procurement.search_text, q))
        if uf:
            stmt = stmt.join(Municipality, Procurement.municipality_id == Municipality.id)
            stmt = stmt.join(State, Municipality.state_id == State.id)
            stmt = stmt.where(State.uf == uf.upper())
        if year:
            stmt = stmt.where(Procurement.year == year)
        if modality:
            stmt = stmt.where(Procurement.modality == str(modality))
        if min_value is not None:
            stmt = stmt.where(Procurement.estimated_total >= min_value)
        if max_value is not None:
            stmt = stmt.where(Procurement.estimated_total <= max_value)

        count = self._count(stmt)
        ranked = stmt.order_by(
            _fts_rank(Procurement.search_text, q).desc(), Procurement.published_at.desc()
        ).offset((page - 1) * page_size).limit(page_size)
        hits = [self._procurement_hit(p) for p in self.db.scalars(ranked)]
        return hits, count

    def _search_contracts(self, q, page, page_size, uf, year):
        stmt = select(Contract).where(_fts_filter(Contract.search_text, q))
        if year:
            stmt = stmt.where(Contract.year == year)
        count = self._count(stmt)
        ranked = stmt.order_by(
            _fts_rank(Contract.search_text, q).desc(), Contract.published_at.desc()
        ).offset((page - 1) * page_size).limit(page_size)
        hits = [self._contract_hit(c) for c in self.db.scalars(ranked)]
        return hits, count

    def _search_suppliers(self, q, page, page_size):
        stmt = select(Supplier).where(_fts_filter(Supplier.search_text, q))
        count = self._count(stmt)
        ranked = stmt.order_by(_fts_rank(Supplier.search_text, q).desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        hits = [self._supplier_hit(s) for s in self.db.scalars(ranked)]
        return hits, count

    def _search_entities(self, q, page, page_size, uf):
        stmt = select(GovernmentEntity).where(_fts_filter(GovernmentEntity.search_text, q))
        if uf:
            stmt = stmt.join(State, GovernmentEntity.state_id == State.id).where(
                State.uf == uf.upper()
            )
        count = self._count(stmt)
        ranked = stmt.order_by(_fts_rank(GovernmentEntity.search_text, q).desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        hits = [self._entity_hit(e) for e in self.db.scalars(ranked)]
        return hits, count

    def _search_municipalities(self, q, page, page_size, uf):
        stmt = select(Municipality).where(_fts_filter(Municipality.search_text, q))
        if uf:
            stmt = stmt.join(State, Municipality.state_id == State.id).where(State.uf == uf.upper())
        count = self._count(stmt)
        ranked = stmt.order_by(_fts_rank(Municipality.search_text, q).desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        hits = [self._municipality_hit(m) for m in self.db.scalars(ranked)]
        return hits, count

    def _search_items(self, q, page, page_size):
        stmt = select(ProcurementItem).where(_fts_filter(ProcurementItem.search_text, q))
        count = self._count(stmt)
        ranked = stmt.order_by(_fts_rank(ProcurementItem.search_text, q).desc()).offset(
            (page - 1) * page_size
        ).limit(page_size)
        hits = [self._item_hit(i) for i in self.db.scalars(ranked)]
        return hits, count

    # --- autocomplete ---
    def suggest(self, q: str, limit: int = 8) -> list[dict[str, Any]]:
        q = (q or "").strip()
        if len(q) < 2:
            return []
        suggestions: list[dict[str, Any]] = []
        per_type = max(2, limit // 3)

        muni_stmt = select(Municipality).where(
            or_(
                _fts_filter(Municipality.search_text, q),
                Municipality.name.ilike(f"%{q}%"),
            )
        ).limit(per_type)
        for m in self.db.scalars(muni_stmt):
            state = self.db.get(State, m.state_id)
            suggestions.append(
                {
                    "type": "municipality",
                    "id": m.id,
                    "label": m.name,
                    "subtitle": state.uf if state else None,
                    "url": f"/municipios/{m.ibge_code}",
                }
            )

        ent_stmt = select(GovernmentEntity).where(
            or_(
                _fts_filter(GovernmentEntity.search_text, q),
                GovernmentEntity.name.ilike(f"%{q}%"),
            )
        ).limit(per_type)
        for e in self.db.scalars(ent_stmt):
            suggestions.append(
                {
                    "type": "entity",
                    "id": e.id,
                    "label": e.name,
                    "subtitle": e.acronym,
                    "url": f"/orgaos/{e.id}",
                }
            )

        sup_stmt = select(Supplier).where(
            or_(_fts_filter(Supplier.search_text, q), Supplier.name.ilike(f"%{q}%"))
        ).limit(per_type)
        for s in self.db.scalars(sup_stmt):
            suggestions.append(
                {
                    "type": "supplier",
                    "id": s.id,
                    "label": s.name,
                    "subtitle": s.document,
                    "url": f"/fornecedores/{s.id}",
                }
            )
        return suggestions[:limit]

    # --- mapeadores de hit ---
    def _location(self, procurement: Procurement) -> str | None:
        if procurement.municipality:
            state = self.db.get(State, procurement.municipality.state_id)
            return f"{procurement.municipality.name}/{state.uf}" if state else procurement.municipality.name
        return None

    def _procurement_hit(self, p: Procurement) -> SearchHit:
        return SearchHit(
            type="procurement",
            id=p.id,
            title=p.object_description[:200],
            subtitle=p.entity.name if p.entity else None,
            value=f"R$ {float(p.estimated_total):,.2f}" if p.estimated_total else None,
            date=p.published_at.date().isoformat() if p.published_at else None,
            location=self._location(p),
            url=f"/contratacoes/{p.id}",
            source_url=p.source_url,
            extra={"modalidade": p.modality_name, "pncp": p.pncp_control_number},
        )

    def _contract_hit(self, c: Contract) -> SearchHit:
        return SearchHit(
            type="contract",
            id=c.id,
            title=c.object_description[:200],
            subtitle=c.supplier.name if c.supplier else None,
            value=f"R$ {float(c.global_value):,.2f}" if c.global_value else None,
            date=c.signed_at.isoformat() if c.signed_at else None,
            url=f"/contratos/{c.id}",
            source_url=c.source_url,
        )

    def _supplier_hit(self, s: Supplier) -> SearchHit:
        return SearchHit(
            type="supplier",
            id=s.id,
            title=s.name,
            subtitle=s.document,
            url=f"/fornecedores/{s.id}",
        )

    def _entity_hit(self, e: GovernmentEntity) -> SearchHit:
        return SearchHit(
            type="entity",
            id=e.id,
            title=e.name,
            subtitle=(e.acronym or e.sphere.value),
            extra={"esfera": e.sphere.value, "poder": e.power.value},
            url=f"/orgaos/{e.id}",
        )

    def _municipality_hit(self, m: Municipality) -> SearchHit:
        state = self.db.get(State, m.state_id)
        return SearchHit(
            type="municipality",
            id=m.id,
            title=m.name,
            subtitle=state.uf if state else None,
            url=f"/municipios/{m.ibge_code}",
        )

    def _item_hit(self, i: ProcurementItem) -> SearchHit:
        return SearchHit(
            type="item",
            id=i.id,
            title=i.description[:200],
            subtitle=i.unit,
            value=f"R$ {float(i.unit_price_estimated):,.2f}/{i.unit}" if i.unit_price_estimated else None,
            url=f"/contratacoes/{i.procurement_id}",
            extra={"item_number": i.item_number, "procurement_id": i.procurement_id},
        )
