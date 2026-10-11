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

from app.connectors.comprasnet import ComprasnetContratosConnector
from app.connectors.pncp import PNCPConnector
from app.connectors.transparencia import TRANSPARENCIA_BASE_URL, TransparenciaConnector
from app.core.logging import get_logger
from app.db.base import utcnow
from app.models.enums import (
    CollectionStatus,
    ContractStatus,
    FinancialStage,
    GovernmentPower,
    GovernmentSphere,
    SourceStatus,
)
from app.models.geo import GovernmentEntity, Municipality, State
from app.models.person import PublicPerson, Remuneration
from app.models.procurement import (
    Contract,
    Payment,
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
                document_type=norm.normalize_document_type(doc_type),
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
        contract.source_system = "pncp"
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

    # ------------------------------------------------------------------ #
    # Comprasnet Contratos (federal, por unidade gestora / UASG)
    # ------------------------------------------------------------------ #
    def _entity_by_uasg(
        self,
        uasg: str,
        name: str,
        state: State | None,
        municipality: Municipality | None,
        source: DataSource,
    ) -> GovernmentEntity:
        """Resolve/cria a entidade do campus por UASG (não por CNPJ institucional).

        Um mesmo CNPJ institucional (ex.: IFSP) é compartilhado por vários campi;
        por isso a identidade confiável da unidade é a UASG.
        """
        entity = self.db.scalar(
            select(GovernmentEntity).where(GovernmentEntity.uasg == uasg)
        )
        if entity is None:
            entity = GovernmentEntity(
                uasg=uasg,
                name=name,
                sphere=GovernmentSphere.FEDERAL,
                power=GovernmentPower.EXECUTIVE,
                state_id=state.id if state else None,
                municipality_id=municipality.id if municipality else None,
                source_id=source.id,
                search_text=norm.build_search_text(name),
            )
            self.db.add(entity)
            self.db.flush()
        else:
            # Mantém o nome/local atualizados sem duplicar a entidade.
            if name and entity.name != name:
                entity.name = name
            if state and entity.state_id is None:
                entity.state_id = state.id
            if municipality and entity.municipality_id is None:
                entity.municipality_id = municipality.id
        return entity

    @staticmethod
    def _map_comprasnet_status(situacao: str | None) -> ContractStatus:
        value = (situacao or "").strip().lower()
        if value.startswith("inativ"):
            return ContractStatus.ENCERRADO
        if value.startswith("ativ"):
            return ContractStatus.VIGENTE
        return ContractStatus.DESCONHECIDO

    def upsert_comprasnet_contract(
        self,
        raw: dict[str, Any],
        source: DataSource,
        run: CollectionRun | None,
        *,
        entity: GovernmentEntity,
        uasg: str,
    ) -> tuple[Contract, bool]:
        """Insere/atualiza um contrato do Comprasnet. Idempotente por (source, id)."""
        external_id = str(raw.get("id") or "").strip()
        if not external_id:
            raise ValueError("Contrato Comprasnet sem identificador (id)")
        if not raw.get("objeto"):
            raise ValueError("Contrato Comprasnet sem objeto")

        # Guarda de segurança: nunca atribuir contrato de outra UASG ao campus.
        raw_uasg = ComprasnetContratosConnector.extract_uasg(raw)
        if str(raw_uasg) != str(uasg):
            raise ValueError(
                f"UASG divergente: contrato {external_id} pertence à unidade "
                f"'{raw_uasg}', esperado '{uasg}'"
            )

        supplier = self._supplier(
            (raw.get("fornecedor") or {}).get("cnpj_cpf_idgener"),
            (raw.get("fornecedor") or {}).get("nome"),
            (raw.get("fornecedor") or {}).get("tipo"),
        )

        signed_at = norm.parse_date(raw.get("data_assinatura"))
        year = signed_at.year if signed_at else None
        if year is None:
            numero = str(raw.get("numero") or "")
            if "/" in numero:
                tail = numero.rsplit("/", 1)[-1]
                year = int(tail) if tail.isdigit() else None

        contract = self.db.scalar(
            select(Contract).where(
                Contract.source_system == "comprasnet",
                Contract.external_id == external_id,
            )
        )
        is_new = contract is None
        if contract is None:
            contract = Contract(
                source_system="comprasnet",
                external_id=external_id,
                source_id=source.id,
                entity_id=entity.id,
                object_description=raw.get("objeto") or "(objeto não informado)",
            )
            self.db.add(contract)

        contract.entity_id = entity.id
        contract.supplier_id = supplier.id if supplier else None
        contract.uasg = str(uasg)
        contract.organization_code = ComprasnetContratosConnector.extract_organization_code(raw)
        contract.contract_type = raw.get("tipo")
        contract.number = raw.get("numero")
        contract.year = year
        contract.process_number = raw.get("processo")
        contract.object_description = raw.get("objeto") or "(objeto não informado)"
        contract.initial_value = norm.parse_decimal(raw.get("valor_inicial"))
        contract.global_value = norm.parse_decimal(raw.get("valor_global"))
        contract.accumulated_value = norm.parse_decimal(raw.get("valor_acumulado"))
        contract.status = self._map_comprasnet_status(raw.get("situacao"))
        contract.signed_at = signed_at
        contract.effective_from = norm.parse_date(raw.get("vigencia_inicio"))
        contract.effective_until = norm.parse_date(raw.get("vigencia_fim"))
        contract.published_at = norm.parse_datetime(raw.get("data_publicacao"))
        contract.collected_at = utcnow()
        contract.collection_run_id = run.id if run else None
        contract.source_url = ComprasnetContratosConnector.contract_source_url(external_id)
        contract.search_text = norm.build_search_text(
            contract.object_description,
            contract.number,
            entity.name,
            (raw.get("fornecedor") or {}).get("nome"),
        )
        self.db.flush()
        return contract, is_new

    def ingest_comprasnet_contracts(
        self,
        uasg: str,
        *,
        include_inactive: bool = True,
        municipality_ibge: str | None = None,
        municipality_name: str | None = None,
        uf: str | None = None,
        max_contracts: int | None = None,
    ) -> CollectionRun:
        """Importa contratos de uma UASG específica (ex.: IFSP Campus Salto)."""
        source = get_source(self.db, "comprasnet")
        params = {
            "uasg": uasg,
            "incluir_inativos": include_inactive,
            "municipio": municipality_ibge,
            "uf": uf,
            "max": max_contracts,
        }
        run = self._start_run(source, scope=f"comprasnet/contratos/ug/{uasg}", params=params)
        stats = IngestionStats()
        status = CollectionStatus.SUCCESS

        state = self._state(uf, None) if uf else None
        municipality = None
        if municipality_ibge:
            municipality = self._municipality(municipality_ibge, municipality_name, state)
            if municipality is None:
                stats.record_error(
                    f"Município {municipality_ibge} não pôde ser resolvido (UF ausente?)"
                )

        try:
            with ComprasnetContratosConnector() as connector:
                records = connector.fetch_unit_contracts_all(
                    uasg, include_inactive=include_inactive
                )
                if max_contracts is not None:
                    records = records[:max_contracts]

                entity: GovernmentEntity | None = None
                if records:
                    unit_name = (
                        ComprasnetContratosConnector.extract_unit_name(records[0])
                        or f"Unidade Gestora {uasg}"
                    )
                    entity = self._entity_by_uasg(
                        str(uasg), unit_name, state, municipality, source
                    )

                for raw in records:
                    stats.fetched += 1
                    try:
                        with self.db.begin_nested():
                            _, is_new = self.upsert_comprasnet_contract(
                                raw, source, run, entity=entity, uasg=str(uasg)
                            )
                            stats.inserted += int(is_new)
                            stats.updated += int(not is_new)
                    except Exception as exc:  # noqa: BLE001 - tolerante por registro
                        stats.record_error(f"{raw.get('id', '?')}: {exc}")
                        logger.warning("Erro ao ingerir contrato Comprasnet: %s", exc)
                    if stats.fetched % 100 == 0:
                        self.db.commit()
                self.db.commit()

            if stats.errors and (stats.inserted + stats.updated):
                status = CollectionStatus.PARTIAL
            elif stats.errors and not (stats.inserted + stats.updated):
                status = CollectionStatus.FAILED
        except Exception as exc:  # noqa: BLE001 - falha da fonte inteira
            stats.record_error(str(exc))
            status = CollectionStatus.FAILED
            logger.exception("Execução Comprasnet falhou: %s", exc)
        finally:
            self._finish_run(run, stats, status)

        return run

    # ------------------------------------------------------------------ #
    # Comprasnet — execução financeira (empenhos e faturas)
    # ------------------------------------------------------------------ #
    def _upsert_payment(
        self,
        contract: Contract,
        *,
        stage: FinancialStage,
        value: Any,
        reference_date: Any,
        external_id: str,
        description: str | None,
        source_url: str | None,
        supplier_id: int | None,
        source: DataSource,
    ) -> bool:
        """Insere/atualiza um lançamento. Retorna True se novo. Nunca usa 0 por padrão."""
        parsed = norm.parse_decimal(value)
        if parsed is None:
            return False

        payment = self.db.scalar(
            select(Payment).where(
                Payment.contract_id == contract.id,
                Payment.external_id == external_id,
            )
        )
        is_new = payment is None
        if payment is None:
            payment = Payment(
                contract_id=contract.id,
                external_id=external_id,
                stage=stage,
                value=parsed,
            )
            self.db.add(payment)

        payment.entity_id = contract.entity_id
        payment.supplier_id = supplier_id
        payment.stage = stage
        payment.value = parsed
        payment.reference_date = norm.parse_date(reference_date)
        payment.description = description
        payment.source_system = source.code
        payment.source_url = source_url or contract.source_url
        self.db.flush()
        return is_new

    def ingest_comprasnet_payments(
        self,
        uasg: str,
        *,
        max_contracts: int | None = None,
    ) -> CollectionRun:
        """Importa os estágios de empenho dos contratos de uma UASG.

        Só importa contratos já sincronizados (source_system='comprasnet', uasg).
        Não confunde valor contratado com valor pago e não duplica estágios
        (as faturas documentam a liquidação, já agregada no empenho).
        """
        source = get_source(self.db, "comprasnet")
        params = {
            "uasg": uasg,
            "max": max_contracts,
        }
        run = self._start_run(source, scope=f"comprasnet/pagamentos/ug/{uasg}", params=params)
        stats = IngestionStats()
        status = CollectionStatus.SUCCESS

        contracts = list(
            self.db.scalars(
                select(Contract)
                .where(
                    Contract.source_system == "comprasnet",
                    Contract.uasg == str(uasg),
                )
                .order_by(Contract.id)
            )
        )
        if max_contracts is not None:
            contracts = contracts[:max_contracts]

        if not contracts:
            stats.record_error(
                f"Nenhum contrato de {uasg} encontrado. Importe contratos antes dos pagamentos."
            )

        try:
            with ComprasnetContratosConnector() as connector:
                for contract in contracts:
                    stats.fetched += 1
                    try:
                        with self.db.begin_nested():
                            self._ingest_contract_payments(
                                connector, contract, source, run, stats
                            )
                    except Exception as exc:  # noqa: BLE001
                        stats.record_error(f"contrato {contract.external_id}: {exc}")
                        logger.warning("Erro ao ingerir pagamentos: %s", exc)
                    if stats.fetched % 50 == 0:
                        self.db.commit()
                self.db.commit()

            if stats.errors and (stats.inserted + stats.updated):
                status = CollectionStatus.PARTIAL
            elif stats.errors and not (stats.inserted + stats.updated):
                status = CollectionStatus.FAILED
        except Exception as exc:  # noqa: BLE001
            stats.record_error(str(exc))
            status = CollectionStatus.FAILED
            logger.exception("Execução de pagamentos Comprasnet falhou: %s", exc)
        finally:
            self._finish_run(run, stats, status)

        return run

    def _ingest_contract_payments(
        self,
        connector: ComprasnetContratosConnector,
        contract: Contract,
        source: DataSource,
        run: CollectionRun | None,
        stats: IngestionStats,
    ) -> None:
        """Persiste os ESTÁGIOS DO EMPENHO (empenhado/liquidado/pago).

        As faturas NÃO viram lançamentos de pagamento: elas documentam a
        liquidação/faturamento que já está agregada nos campos do empenho.
        Somar ambos contaria o mesmo dinheiro duas vezes. As faturas permanecem
        disponíveis na fonte oficial como documento de apoio.
        """
        supplier_id: int | None = None

        for emp in connector.fetch_contract_commitments(contract.external_id or ""):
            credor = emp.get("credor_obj") or {}
            supplier = self._supplier(
                credor.get("cnpj_cpf_idgener"),
                credor.get("nome"),
                credor.get("tipo"),
            )
            if supplier is not None:
                supplier_id = supplier.id
            payment_link = (emp.get("links") or {}).get("documento_pagamento")
            numero = emp.get("numero") or emp.get("id")
            natureza = emp.get("naturezadespesa") or ""
            for stage_name, value in (
                ("empenhado", emp.get("empenhado")),
                ("liquidado", emp.get("liquidado")),
                ("pago", emp.get("pago")),
            ):
                stage = {
                    "empenhado": FinancialStage.EMPENHADO,
                    "liquidado": FinancialStage.LIQUIDADO,
                    "pago": FinancialStage.PAGO,
                }[stage_name]
                is_new = self._upsert_payment(
                    contract,
                    stage=stage,
                    value=value,
                    reference_date=emp.get("data_emissao"),
                    external_id=f"empenho:{emp.get('id')}:{stage_name}",
                    description=f"Empenho {numero} — {natureza}".strip(" —"),
                    source_url=payment_link,
                    supplier_id=supplier_id,
                    source=source,
                )
                stats.inserted += int(is_new)
                stats.updated += int(not is_new and value is not None)

    # ------------------------------------------------------------------ #
    # Portal da Transparência — servidores e remuneração (Exige chave)
    # ------------------------------------------------------------------ #
    def _entity_for_campus(self, campus_name: str | None) -> GovernmentEntity | None:
        """Localiza a entidade (campus) cujo nome normalizado coincide com a UORG."""
        if not campus_name:
            return None
        target = norm.normalize_text(campus_name)
        for entity in self.db.scalars(select(GovernmentEntity)):
            if norm.normalize_text(entity.name) == target:
                return entity
        return None

    def _upsert_person(
        self,
        name: str,
        masked_document: str | None,
        role_title: str | None,
        entity: GovernmentEntity | None,
        source: DataSource,
    ) -> PublicPerson:
        person = self.db.scalar(
            select(PublicPerson).where(
                PublicPerson.name == name,
                PublicPerson.entity_id == (entity.id if entity else None),
            )
        )
        if person is None:
            person = PublicPerson(
                name=name,
                masked_document=masked_document,
                role_title=role_title,
                entity_id=entity.id if entity else None,
                source_id=source.id,
                search_text=norm.build_search_text(name, role_title, entity.name if entity else None),
            )
            self.db.add(person)
            self.db.flush()
        else:
            if masked_document and not person.masked_document:
                person.masked_document = masked_document
            if role_title and not person.role_title:
                person.role_title = role_title
        return person

    def _upsert_remuneration(
        self,
        person: PublicPerson,
        entity: GovernmentEntity | None,
        info: dict[str, Any],
        source_url: str | None,
    ) -> bool:
        year, month = info.get("year"), info.get("month")
        existing = self.db.scalar(
            select(Remuneration).where(
                Remuneration.person_id == person.id,
                Remuneration.reference_year == year,
                Remuneration.reference_month == month,
            )
        )
        is_new = existing is None
        remuneration = existing or Remuneration(person_id=person.id)
        if is_new:
            self.db.add(remuneration)
        remuneration.entity_id = entity.id if entity else None
        remuneration.reference_year = year
        remuneration.reference_month = month
        remuneration.gross_amount = norm.parse_decimal(info.get("gross"))
        remuneration.net_amount = norm.parse_decimal(info.get("net"))
        remuneration.source_url = source_url
        remuneration.reference_date = None
        self.db.flush()
        return is_new

    def ingest_transparencia_servidores(
        self,
        orgao_code: str,
        mes_ano: str,
        *,
        campus_uorg: str | None = None,
        max_servidores: int | None = None,
    ) -> CollectionRun:
        """Importa servidores e remunerações de um órgão federal.

        Exige `TRANSPARENCIA_API_KEY`. Se `campus_uorg` for informado, apenas
        servidores cuja lotação (UORG) corresponder são associados ao campus —
        evitando atribuir todos os servidores do IFSP a um único campus.
        """
        source = get_source(self.db, "transparencia")
        params = {
            "orgao": orgao_code,
            "mesAno": mes_ano,
            "campus_uorg": campus_uorg,
            "max": max_servidores,
        }
        run = self._start_run(
            source, scope=f"transparencia/servidores/orgao/{orgao_code}", params=params
        )
        stats = IngestionStats()
        status = CollectionStatus.SUCCESS
        uri = f"{TRANSPARENCIA_BASE_URL}/servidores?orgaoServidorLotacao={orgao_code}"

        try:
            with TransparenciaConnector() as connector:
                if not connector.credentials_available:
                    stats.record_error(
                        "Credencial ausente: TRANSPARENCIA_API_KEY não configurada. "
                        "Nenhum dado de remuneração foi importado."
                    )
                    status = CollectionStatus.FAILED
                else:
                    servidores = connector.fetch_servidores(orgao_code)
                    if max_servidores is not None:
                        servidores = servidores[:max_servidores]
                    skipped_other_campus = 0
                    for servidor in servidores:
                        stats.fetched += 1
                        try:
                            with self.db.begin_nested():
                                sid = servidor.get("id") or servidor.get("idServidorAposentadoPensionista")
                                detail = connector.fetch_servidor(sid) if sid else None
                                campus = TransparenciaConnector.extract_campus_uorg(detail)
                                if campus_uorg and campus and norm.normalize_text(campus) != norm.normalize_text(campus_uorg):
                                    skipped_other_campus += 1
                                    stats.skipped += 1
                                    continue
                                name = TransparenciaConnector.extract_name(servidor) or (
                                    TransparenciaConnector.extract_name(detail or {})
                                )
                                if not name:
                                    stats.skipped += 1
                                    continue
                                entity = self._entity_for_campus(campus)
                                person = self._upsert_person(
                                    name,
                                    TransparenciaConnector.extract_masked_document(servidor),
                                    TransparenciaConnector.extract_role(servidor),
                                    entity,
                                    source,
                                )
                                for rem in connector.fetch_remuneracao(sid, mes_ano):
                                    info = TransparenciaConnector.extract_remuneracao(rem)
                                    is_new = self._upsert_remuneration(person, entity, info, uri)
                                    stats.inserted += int(is_new)
                                    stats.updated += int(not is_new)
                        except Exception as exc:  # noqa: BLE001
                            stats.record_error(f"{servidor.get('id', '?')}: {exc}")
                    if skipped_other_campus:
                        logger.info(
                            "Servidores de outros campi ignorados: %s", skipped_other_campus
                        )
                    self.db.commit()

                    if stats.errors and (stats.inserted + stats.updated):
                        status = CollectionStatus.PARTIAL
                    elif stats.errors and not (stats.inserted + stats.updated):
                        status = CollectionStatus.FAILED
        except Exception as exc:  # noqa: BLE001
            stats.record_error(str(exc))
            status = CollectionStatus.FAILED
            logger.exception("Execução de servidores do Portal da Transparência falhou: %s", exc)
        finally:
            self._finish_run(run, stats, status)

        return run
