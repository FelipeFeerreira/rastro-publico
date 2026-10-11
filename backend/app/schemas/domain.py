"""Schemas de domínio (fontes, órgãos, fornecedores, contratações, contratos)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None = None
    homepage_url: str
    api_documentation_url: str | None = None
    license_name: str | None = None
    license_url: str | None = None
    status: str
    requires_authentication: bool
    coverage_description: str | None = None
    last_success_at: datetime | None = None
    last_checked_at: datetime | None = None


class CollectionRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int
    status: str
    scope: str | None = None
    started_at: datetime
    finished_at: datetime | None = None
    records_fetched: int
    records_inserted: int
    records_updated: int
    records_skipped: int
    error_count: int
    message: str | None = None


class StateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ibge_code: str
    uf: str
    name: str


class MunicipalityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ibge_code: str
    name: str
    state_id: int
    uf: str | None = None


class EntitySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cnpj: str | None = None
    uasg: str | None = None
    name: str
    acronym: str | None = None
    sphere: str
    power: str
    municipality_id: int | None = None
    state_id: int | None = None


class SupplierSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    document: str
    document_type: str | None = None
    is_individual: bool


class SupplierDetail(SupplierSummary):
    contract_count: int = 0
    total_contract_value: Decimal | None = None
    procurement_count: int = 0


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    item_number: int
    description: str
    kind: str
    unit: str | None = None
    quantity: Decimal | None = None
    unit_price_estimated: Decimal | None = None
    total_estimated: Decimal | None = None
    judgment_criteria: str | None = None
    situation: str | None = None
    category_key: str | None = None


class ResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    item_id: int
    supplier_id: int | None = None
    supplier_name: str | None = None
    supplier_document: str | None = None
    unit_price: Decimal | None = None
    quantity: Decimal | None = None
    total_price: Decimal | None = None
    result_date: date | None = None
    status: str | None = None
    source_url: str | None = None


class ProcurementSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    pncp_control_number: str
    number: str | None = None
    object_description: str
    modality: str
    modality_name: str | None = None
    status: str
    status_name: str | None = None
    estimated_total: Decimal | None = None
    approved_total: Decimal | None = None
    published_at: datetime | None = None
    entity: EntitySummary | None = None
    municipality: MunicipalityOut | None = None
    source_url: str | None = None


class ProcurementDetail(ProcurementSummary):
    process_number: str | None = None
    additional_info: str | None = None
    is_price_registry: bool = False
    is_parliamentary_amendment: bool | None = None
    dispute_mode_name: str | None = None
    proposal_open_at: datetime | None = None
    proposal_close_at: datetime | None = None
    source_updated_at: datetime | None = None
    collected_at: datetime | None = None
    origin_system_link: str | None = None
    items: list[ItemOut] = Field(default_factory=list)
    results: list[ResultOut] = Field(default_factory=list)
    source: SourceOut | None = None


class ContractSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_system: str = "pncp"
    external_id: str | None = None
    uasg: str | None = None
    organization_code: str | None = None
    contract_type: str | None = None
    accumulated_value: Decimal | None = None
    pncp_control_number: str | None = None
    number: str | None = None
    object_description: str
    global_value: Decimal | None = None
    initial_value: Decimal | None = None
    signed_at: date | None = None
    effective_from: date | None = None
    effective_until: date | None = None
    status: str
    supplier: SupplierSummary | None = None
    entity: EntitySummary | None = None
    source_url: str | None = None
    # Soma dos lançamentos PAGOS do contrato (não é o valor contratado).
    paid_value: Decimal | None = None


class AmendmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    term_number: str | None = None
    amendment_type: str | None = None
    value_added: Decimal | None = None
    value_reduced: Decimal | None = None
    new_value: Decimal | None = None
    new_end_date: date | None = None
    signed_at: date | None = None
    description: str | None = None
    source_url: str | None = None


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    contract_id: int | None = None
    stage: str
    value: Decimal
    reference_date: date | None = None
    external_id: str | None = None
    description: str | None = None
    source_system: str = "pncp"
    source_url: str | None = None
    supplier_id: int | None = None


class PaymentSummary(BaseModel):
    """Resumo por estágio. Nunca somar estágios distintos como se fossem o mesmo."""

    empenhado: Decimal = Decimal("0")
    liquidado: Decimal = Decimal("0")
    pago: Decimal = Decimal("0")
    count: int = 0


class ContractDetail(ContractSummary):
    process_number: str | None = None
    published_at: datetime | None = None
    amendments: list[AmendmentOut] = Field(default_factory=list)
    payment_summary: PaymentSummary | None = None
    source: SourceOut | None = None


class CampusTotals(BaseModel):
    contracts: int = 0
    suppliers: int = 0
    first_contract_date: date | None = None
    last_contract_date: date | None = None
    last_collection_at: datetime | None = None


class CampusFinancials(BaseModel):
    """Estágios mantidos separados. Nunca somar estágios diferentes entre si."""

    contracted: Decimal = Decimal("0")
    committed: Decimal = Decimal("0")
    liquidated: Decimal = Decimal("0")
    paid: Decimal = Decimal("0")
    payment_events: int = 0


class CampusDashboard(BaseModel):
    entity: EntitySummary
    uasg: str
    municipality_name: str | None = None
    uf: str | None = None
    is_federal: bool = True
    totals: CampusTotals
    financials: CampusFinancials
    source: SourceOut | None = None
    notes: list[str] = Field(default_factory=list)
