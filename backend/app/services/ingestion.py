"""Serviço de ingestão: conecta fontes públicas ao banco normalizado.

Fluxo: conector -> normalização -> deduplicação -> persistência, com registro
de cada execução em `collection_runs`, contadores e log de erros recuperáveis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.pncp import PNCPConnector
from app.core.logging import get_logger
from app.db.base import utcnow
from app.models.enums import (
    CollectionStatus,
    GovernmentPower,
    GovernmentSphere,
    SourceStatus,
)
from app.models.geo import GovernmentEntity, Municipality, State
from app.models.procurement import (
    Contract,
    Procurement,
    ProcurementItem,
    ProcurementResult,
)
from app.models.source import CollectionRun, DataSource
from app.models.supplier import Supplier
from app.services import normalization as norm
from app.services.reference_data import get_source

logger = get_logger(__name__)

_ESFERA = {"F": GovernmentSphere.FEDERAL, "E": GovernmentSphere.STATE,
           "M": GovernmentSphere.MUNICIPAL, "D": GovernmentSphere.MUNICIPAL}
_PODER = {"E": GovernmentPower.EXECUTIVE, "L": GovernmentPower.LEGISLATIVE,
          "J": GovernmentPower.JUDICIARY, "N": GovernmentPower.OTHER}


@dataclass
class IngestionStats:
    fetched: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    error_log: list[str] = field(default_factory=list)

    def record_error(self, message: str) -> None:
        self.errors += 1
        if len(self.error_log) < 50:
            self.error_log.append(message)


class IngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------ #
    # Helpers de resolução de entidades de referência
    # ------------------------------------------------------------------ #
    def _state(self, uf: str | None, name: str | None) -> State | None:
        if not uf:
            return None
        state = self.db.scalar(select(State).where(State.uf == uf.upper()))
        if state is None:
            state = State(uf=uf.upper()[:2], ibge_code="", name=name or uf.upper())
            self.db.add(state)
            self.db.flush()
        return state

    def _municipality(
        self, ibge: str | None, name: str | None, state: State | None
    ) -> Municipality | None:
        if not ibge:
            return None
        municipality = self.db.scalar(
            select(Municipality).where(Municipality.ibge_code == ibge)
        )
        if municipality is None:
            municipality = Municipality(
                ibge_code=ibge,
                name=name or ibge,
                state_id=state.id if state else None,
                search_text=norm.build_search_text(name, state.name if state else None),
            )
            if state is None:
                # Município sem UF conhecida não pode ser persistido (FK obrigatória).
                return None
            self.db.add(municipality)
            self.db.flush()
        return municipality

    def _entity(
        self,
        cnpj: str | None,
        name: str,
        esfera: str | None,
        poder: str | None,
        state: State | None,
        municipality: Municipality | None,
        source: DataSource,
    ) -> GovernmentEntity | None:
        if not name:
            return None
        query = select(GovernmentEntity)
        entity = None
        if cnpj:
            entity = self.db.scalar(query.where(GovernmentEntity.cnpj == cnpj))
        if entity is None and not cnpj:
            entity = self.db.scalar(
                query.where(
                    GovernmentEntity.name == name,
                    GovernmentEntity.municipality_id
                    == (municipality.id if municipality else None),
                )
            )
        if entity is None:
            entity = GovernmentEntity(
                cnpj=cnpj,
                name=name,
                sphere=_ESFERA.get((esfera or "").upper(), GovernmentSphere.OTHER),
                power=_PODER.get((poder or "").upper(), GovernmentPower.OTHER),
                state_id=state.id if state else None,
                municipality_id=municipality.id if municipality else None,
                source_id=source.id,
                search_text=norm.build_search_text(name),
            )
            self.db.add(entity)
            self.db.flush()
        return entity

    def _supplier(
        self, document: str | None, name: str | None, doc_type: str | None
    ) -> Supplier | None:
        doc = norm.normalize_document(document)
        if not doc:
            return None
        supplier = self.db.scalar(select(Supplier).where(Supplier.document == doc))
        if supplier is None:
            display_name = name or doc
            supplier = Supplier(
                document=doc,
                document_type=doc_type,
                name=display_name,
                is_individual=len(doc) == 11,
                search_text=norm.build_search_text(display_name),
            )
            self.db.add(supplier)
            self.db.flush()
        return supplier

    # ------------------------------------------------------------------ #
    # Contratações
    # ------------------------------------------------------------------ #
    def upsert_procurement(
        self, raw: dict[str, Any], source: DataSource, run: CollectionRun | None
    ) -> tuple[Procurement, bool]:
        """Insere/atualiza uma contratação. Retorna (procurement, is_new)."""
        control = raw.get("numeroControlePNCP")
        if not control:
            raise ValueError("Contratação sem numeroControlePNCP")

        unidade = raw.get("unidadeOrgao") or {}
        orgao = raw.get("orgaoEntidade") or {}

        state = self._state(unidade.get("ufSigla"), unidade.get("ufNome"))
        municipality = self._municipality(
            unidade.get("codigoIbge"), unidade.get("municipioNome"), state
        )
        entity = self._entity(
            norm.only_digits(orgao.get("cnpj")) or None,
            orgao.get("razaoSocial") or unidade.get("nomeUnidade") or "",
            orgao.get("esferaId"),
            orgao.get("poderId"),
            state,
            municipality,
            source,
        )
        if entity is None:
            raise ValueError("Contratação sem órgão/entidade identificável")

        modality = norm.map_modality(raw.get("modalidadeId"))
        status = norm.map_procurement_status(raw.get("situacaoCompraNome"))
        published = norm.parse_datetime(raw.get("dataPublicacaoPncp"))
        search_text = norm.build_search_text(
            raw.get("objetoCompra"),
            raw.get("numeroCompra"),
            raw.get("processo"),
            orgao.get("razaoSocial"),
            unidade.get("municipioNome"),
            raw.get("modalidadeNome"),
        )

        procurement = self.db.scalar(
            select(Procurement).where(Procurement.pncp_control_number == control)
        )
        is_new = procurement is None
        if procurement is None:
            procurement = Procurement(
                pncp_control_number=control,
                entity_id=entity.id,
                source_id=source.id,
            )
            self.db.add(procurement)

        procurement.entity_id = entity.id
        procurement.municipality_id = municipality.id if municipality else None
        procurement.year = int(raw.get("anoCompra") or 0)
        procurement.sequential = int(raw.get("sequencialCompra") or 0)
        procurement.number = raw.get("numeroCompra")
        procurement.process_number = raw.get("processo")
        procurement.modality = modality
        procurement.modality_name = raw.get("modalidadeNome")
        procurement.dispute_mode_name = raw.get("modoDisputaNome")
        procurement.status = status
        procurement.status_name = raw.get("situacaoCompraNome")
        procurement.object_description = raw.get("objetoCompra") or "(objeto não informado)"
        procurement.additional_info = raw.get("informacaoComplementar")
        procurement.is_price_registry = bool(raw.get("srp"))
        procurement.is_parliamentary_amendment = raw.get("emendaParlamentar")
        procurement.estimated_total = norm.parse_decimal(raw.get("valorTotalEstimado"))
        procurement.approved_total = norm.parse_decimal(raw.get("valorTotalHomologado"))
        procurement.published_at = published
        procurement.proposal_open_at = norm.parse_datetime(raw.get("dataAberturaProposta"))
        procurement.proposal_close_at = norm.parse_datetime(raw.get("dataEncerramentoProposta"))
        procurement.source_updated_at = norm.parse_datetime(raw.get("dataAtualizacao"))
        procurement.collected_at = utcnow()
        procurement.origin_system_link = raw.get("linkSistemaOrigem") or raw.get(
            "linkProcessoEletronico"
        )
        cnpj_digits = norm.only_digits(orgao.get("cnpj"))
        procurement.source_url = (
            PNCPConnector.public_url(cnpj_digits, procurement.year, procurement.sequential)
            if cnpj_digits and procurement.year and procurement.sequential
            else None
        )
        procurement.collection_run_id = run.id if run else None
        procurement.search_text = search_text

        self.db.flush()
        return procurement, is_new

    def ingest_items(self, procurement: Procurement, connector: PNCPConnector) -> int:
        """Busca e persiste itens (e resultados homologados) de uma contratação."""
        entity = procurement.entity
        cnpj = entity.cnpj if entity else None
        if not cnpj:
            return 0

        try:
            raw_items = connector.fetch_items(cnpj, procurement.year, procurement.sequential)
        except Exception as exc:  # noqa: BLE001 - tolerante por item
            logger.warning("Falha ao buscar itens de %s: %s", procurement.pncp_control_number, exc)
            return 0

        count = 0
        for raw in raw_items:
            number = int(raw.get("numeroItem") or 0)
            if not number:
                continue
            item = self.db.scalar(
                select(ProcurementItem).where(
                    ProcurementItem.procurement_id == procurement.id,
                    ProcurementItem.item_number == number,
                )
            )
            if item is None:
                item = ProcurementItem(procurement_id=procurement.id, item_number=number)
                self.db.add(item)

            item.description = raw.get("descricao") or "(item sem descrição)"
            item.kind = norm.map_item_kind(raw.get("materialOuServico"), item.description)
            item.unit = raw.get("unidadeMedida")
            item.quantity = norm.parse_decimal(raw.get("quantidade"))
            item.unit_price_estimated = norm.parse_decimal(raw.get("valorUnitarioEstimado"))
            item.total_estimated = norm.parse_decimal(raw.get("valorTotal"))
            item.judgment_criteria = raw.get("criterioJulgamentoNome")
            item.situation = raw.get("situacaoCompraItemNome")
            item.category_key = norm.derive_category_key(
                item.description, str(raw.get("codigoItemCatalogo") or "") or None
            )
            item.search_text = norm.build_search_text(item.description, item.unit)
            self.db.flush()

            try:
                results = connector.fetch_item_results(
                    cnpj, procurement.year, procurement.sequential, number
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("Sem resultados para item %s: %s", number, exc)
                results = []

            for raw_result in results:
                self._upsert_result(procurement, item, raw_result)
            count += 1

        self.db.flush()
        return count

    def _upsert_result(
        self, procurement: Procurement, item: ProcurementItem, raw: dict[str, Any]
    ) -> None:
        sequential = raw.get("sequencialResultado")
        result = self.db.scalar(
            select(ProcurementResult).where(
                ProcurementResult.item_id == item.id,
                ProcurementResult.result_sequential == sequential,
            )
        )
        if result is None:
            result = ProcurementResult(
                procurement_id=procurement.id,
                item_id=item.id,
                result_sequential=sequential,
            )
            self.db.add(result)

        supplier = self._supplier(
            raw.get("niFornecedor"),
            raw.get("nomeRazaoSocialFornecedor"),
            raw.get("tipoPessoa"),
        )
        result.supplier_id = supplier.id if supplier else None
        result.supplier_document = norm.normalize_document(raw.get("niFornecedor"))
        result.supplier_name = raw.get("nomeRazaoSocialFornecedor")
        result.unit_price = norm.parse_decimal(raw.get("valorUnitarioHomologado"))
        result.quantity = norm.parse_decimal(raw.get("quantidadeHomologada"))
        result.total_price = norm.parse_decimal(raw.get("valorTotalHomologado"))
        result.result_date = norm.parse_date(raw.get("dataResultado"))
        result.status = raw.get("situacaoCompraItemResultadoNome")
        result.source_url = procurement.source_url

    # ------------------------------------------------------------------ #
    # Orquestração de uma execução
    # ------------------------------------------------------------------ #
    def _start_run(self, source: DataSource, scope: str, params: dict[str, Any]) -> CollectionRun:
        run = CollectionRun(
            source_id=source.id,
            status=CollectionStatus.RUNNING,
            scope=scope,
            parameters=params,
            started_at=utcnow(),
        )
        self.db.add(run)
        self.db.flush()
        return run

    def _finish_run(self, run: CollectionRun, stats: IngestionStats, status: CollectionStatus) -> None:
        run.status = status
        run.finished_at = utcnow()
        run.records_fetched = stats.fetched
        run.records_inserted = stats.inserted
        run.records_updated = stats.updated
        run.records_skipped = stats.skipped
        run.error_count = stats.errors
        run.error_log = stats.error_log or None
        run.message = (
            f"{stats.inserted} inseridos, {stats.updated} atualizados, "
            f"{stats.errors} erros"
        )
        source = self.db.get(DataSource, run.source_id)
        if source is not None:
            source.last_checked_at = utcnow()
            if status in (CollectionStatus.SUCCESS, CollectionStatus.PARTIAL):
                source.last_success_at = utcnow()
                source.status = SourceStatus.ACTIVE
            elif status == CollectionStatus.FAILED:
                source.status = SourceStatus.DEGRADED
        self.db.commit()

    def ingest_pncp_publications(
        self,
        start: date | datetime,
        end: date | datetime,
        *,
        modality_codes: list[int] | None = None,
        uf: str | None = None,
        municipality_ibge: str | None = None,
        cnpj: str | None = None,
        with_items: bool = False,
        max_pages_per_modality: int | None = None,
    ) -> CollectionRun:
        source = get_source(self.db, "pncp")
        params = {
            "inicio": str(start),
            "fim": str(end),
            "modalidades": modality_codes or "todas",
            "uf": uf,
            "municipio": municipality_ibge,
            "cnpj": cnpj,
            "com_itens": with_items,
        }
        run = self._start_run(source, scope="pncp/contratacoes/publicacao", params=params)
        stats = IngestionStats()
        status = CollectionStatus.SUCCESS

        try:
            with PNCPConnector() as connector:
                for raw in connector.iter_publications(
                    start,
                    end,
                    modality_codes=modality_codes,
                    uf=uf,
                    municipality_ibge=municipality_ibge,
                    cnpj=cnpj,
                    max_pages_per_modality=max_pages_per_modality,
                ):
                    stats.fetched += 1
                    try:
                        with self.db.begin_nested():
                            procurement, is_new = self.upsert_procurement(raw, source, run)
                            if is_new:
                                stats.inserted += 1
                            else:
                                stats.updated += 1
                            if with_items:
                                self.ingest_items(procurement, connector)
                    except Exception as exc:  # noqa: BLE001
                        stats.record_error(f"{raw.get('numeroControlePNCP', '?')}: {exc}")
                        logger.warning("Erro ao ingerir contratação: %s", exc)
                    # Commita em lotes para não perder progresso em execuções longas.
                    if stats.fetched % 200 == 0:
                        self.db.commit()
            if stats.errors and (stats.inserted + stats.updated):
                status = CollectionStatus.PARTIAL
            elif stats.errors and not (stats.inserted + stats.updated):
                status = CollectionStatus.FAILED
        except Exception as exc:  # noqa: BLE001 - falha da fonte inteira
            stats.record_error(str(exc))
            status = CollectionStatus.FAILED
            logger.exception("Execução PNCP falhou: %s", exc)
        finally:
            self._finish_run(run, stats, status)

        return run

    # ------------------------------------------------------------------ #
    # Contratos (base PNCP /v1/contratos)
    # ------------------------------------------------------------------ #
    def ingest_pncp_contracts(
        self,
        start: date | datetime,
        end: date | datetime,
        *,
        cnpj: str | None = None,
        max_pages: int | None = None,
    ) -> CollectionRun:
        source = get_source(self.db, "pncp")
        run = self._start_run(
            source,
            scope="pncp/contratos",
            params={"inicio": str(start), "fim": str(end), "cnpj": cnpj},
        )
        stats = IngestionStats()
        status = CollectionStatus.SUCCESS
        try:
            with PNCPConnector() as connector:
                for raw in connector.iter_contracts(start, end, cnpj=cnpj, max_pages=max_pages):
                    stats.fetched += 1
                    try:
                        with self.db.begin_nested():
                            _, is_new = self.upsert_contract(raw, source, run)
                            stats.inserted += int(is_new)
                            stats.updated += int(not is_new)
                    except Exception as exc:  # noqa: BLE001
                        stats.record_error(str(exc))
                self.db.commit()
            if stats.errors:
                status = CollectionStatus.PARTIAL
        except Exception as exc:  # noqa: BLE001
            stats.record_error(str(exc))
            status = CollectionStatus.FAILED
            logger.exception("Execução de contratos PNCP falhou: %s", exc)
        finally:
            self._finish_run(run, stats, status)
        return run

    def upsert_contract(
        self, raw: dict[str, Any], source: DataSource, run: CollectionRun | None
    ) -> tuple[Contract, bool]:
        control = raw.get("numeroControlePNCP") or raw.get("numeroControlePncpCompra")
        if not control:
            raise ValueError("Contrato sem numeroControlePNCP")

        unidade = raw.get("unidadeOrgao") or {}
        orgao = raw.get("orgaoEntidade") or {}
        state = self._state(unidade.get("ufSigla"), unidade.get("ufNome"))
        municipality = self._municipality(
            unidade.get("codigoIbge"), unidade.get("municipioNome"), state
        )
        entity = self._entity(
            norm.only_digits(orgao.get("cnpj")) or None,
            orgao.get("razaoSocial") or "",
            orgao.get("esferaId"),
            orgao.get("poderId"),
            state,
            municipality,
            source,
        )
        if entity is None:
            raise ValueError("Contrato sem órgão/entidade identificável")

        supplier = self._supplier(
            raw.get("niFornecedor"),
            raw.get("nomeRazaoSocialFornecedor"),
            raw.get("tipoPessoa"),
        )

        contract = self.db.scalar(
            select(Contract).where(Contract.pncp_control_number == control)
        )
        is_new = contract is None
        if contract is None:
            contract = Contract(
                pncp_control_number=control, entity_id=entity.id, source_id=source.id
            )
            self.db.add(contract)

        contract.entity_id = entity.id
        contract.supplier_id = supplier.id if supplier else None
        contract.year = raw.get("anoContrato")
        contract.sequential = raw.get("sequencialContrato")
        contract.number = raw.get("numeroContratoEmpenho")
        contract.process_number = raw.get("processo")
        contract.object_description = raw.get("objetoContrato") or "(objeto não informado)"
        contract.initial_value = norm.parse_decimal(raw.get("valorInicial"))
        contract.global_value = norm.parse_decimal(raw.get("valorGlobal"))
        contract.signed_at = norm.parse_date(raw.get("dataAssinatura"))
        contract.effective_from = norm.parse_date(raw.get("dataVigenciaInicio"))
        contract.effective_until = norm.parse_date(raw.get("dataVigenciaFim"))
        contract.published_at = norm.parse_datetime(raw.get("dataPublicacaoPncp"))
        contract.collected_at = utcnow()
        contract.collection_run_id = run.id if run else None
        contract.search_text = norm.build_search_text(
            contract.object_description,
            contract.number,
            orgao.get("razaoSocial"),
            raw.get("nomeRazaoSocialFornecedor"),
        )
        self.db.flush()
        return contract, is_new
