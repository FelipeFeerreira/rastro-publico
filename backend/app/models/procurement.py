"""Contratações, itens, resultados, contratos, aditivos e pagamentos."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    ContractStatus,
    FinancialStage,
    ItemKind,
    ProcurementModality,
    ProcurementStatus,
)


class Procurement(Base, TimestampMixin):
    """Contratação publicada no PNCP (edital, aviso, dispensa, etc.)."""

    __tablename__ = "procurements"
    __table_args__ = (
        Index("ix_procurements_modality", "modality"),
        Index("ix_procurements_pncp_number", "pncp_control_number", unique=True),
        Index("ix_procurements_entity_year", "entity_id", "year"),
        Index("ix_procurements_municipality_year", "municipality_id", "year"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    entity_id: Mapped[int] = mapped_column(ForeignKey("government_entities.id"), nullable=False)
    municipality_id: Mapped[int | None] = mapped_column(ForeignKey("municipalities.id"))

    pncp_control_number: Mapped[str] = mapped_column(String(40), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    sequential: Mapped[int] = mapped_column(Integer, nullable=False)
    number: Mapped[str | None] = mapped_column(String(50))
    process_number: Mapped[str | None] = mapped_column(String(80))

    modality: Mapped[ProcurementModality] = mapped_column(
        Enum(ProcurementModality, native_enum=False, length=30),
        default=ProcurementModality.DESCONHECIDA,
        nullable=False,
    )
    modality_name: Mapped[str | None] = mapped_column(String(120))
    dispute_mode_name: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[ProcurementStatus] = mapped_column(
        Enum(ProcurementStatus, native_enum=False, length=20),
        default=ProcurementStatus.DESCONHECIDA,
        nullable=False,
    )
    status_name: Mapped[str | None] = mapped_column(String(120))

    object_description: Mapped[str] = mapped_column(Text, nullable=False)
    additional_info: Mapped[str | None] = mapped_column(Text)

    is_price_registry: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_parliamentary_amendment: Mapped[bool | None] = mapped_column(Boolean)

    # Estágios financeiros distintos. Nunca confundir um com o outro.
    estimated_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    approved_total: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    proposal_open_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    proposal_close_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    origin_system_link: Mapped[str | None] = mapped_column(String(600))
    source_url: Mapped[str | None] = mapped_column(String(600))
    collection_run_id: Mapped[int | None] = mapped_column(ForeignKey("collection_runs.id"))
    search_text: Mapped[str | None] = mapped_column(Text)

    entity = relationship("GovernmentEntity", back_populates="procurements")
    municipality = relationship("Municipality")
    source = relationship("DataSource")
    items = relationship(
        "ProcurementItem", back_populates="procurement", cascade="all, delete-orphan"
    )
    contracts = relationship("Contract", back_populates="procurement")


class ProcurementItem(Base, TimestampMixin):
    __tablename__ = "procurement_items"
    __table_args__ = (
        Index("ix_procurement_items_procurement", "procurement_id", "item_number", unique=True),
        Index("ix_procurement_items_kind", "kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    procurement_id: Mapped[int] = mapped_column(
        ForeignKey("procurements.id", ondelete="CASCADE"), nullable=False
    )
    item_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[ItemKind] = mapped_column(
        Enum(ItemKind, native_enum=False, length=15),
        default=ItemKind.DESCONHECIDO,
        nullable=False,
    )
    unit: Mapped[str | None] = mapped_column(String(60))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    unit_price_estimated: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    total_estimated: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    judgment_criteria: Mapped[str | None] = mapped_column(String(120))
    situation: Mapped[str | None] = mapped_column(String(120))
    catalog_code: Mapped[str | None] = mapped_column(String(60))
    # Chave de comparabilidade derivada (catálogo oficial ou heurística).
    category_key: Mapped[str | None] = mapped_column(String(120), index=True)
    search_text: Mapped[str | None] = mapped_column(Text)

    procurement = relationship("Procurement", back_populates="items")
    results = relationship(
        "ProcurementResult", back_populates="item", cascade="all, delete-orphan"
    )


class ProcurementResult(Base, TimestampMixin):
    """Resultado homologado de um item: fornecedor vencedor e preço unitário."""

    __tablename__ = "procurement_results"
    __table_args__ = (
        Index("ix_procurement_results_item", "item_id"),
        Index("ix_procurement_results_supplier", "supplier_id"),
        Index("ix_procurement_results_unit_price", "unit_price"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    procurement_id: Mapped[int] = mapped_column(
        ForeignKey("procurements.id", ondelete="CASCADE"), nullable=False
    )
    item_id: Mapped[int] = mapped_column(
        ForeignKey("procurement_items.id", ondelete="CASCADE"), nullable=False
    )
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"))
    result_sequential: Mapped[int | None] = mapped_column(Integer)
    supplier_document: Mapped[str | None] = mapped_column(String(14))
    supplier_name: Mapped[str | None] = mapped_column(String(300))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    total_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    result_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str | None] = mapped_column(String(60))
    source_url: Mapped[str | None] = mapped_column(String(600))

    item = relationship("ProcurementItem", back_populates="results")
    supplier = relationship("Supplier", back_populates="procurements_won")


class Contract(Base, TimestampMixin):
    __tablename__ = "contracts"
    __table_args__ = (
        Index("ix_contracts_pncp_number", "pncp_control_number", unique=True),
        Index("ix_contracts_supplier", "supplier_id"),
        Index("ix_contracts_entity_year", "entity_id", "year"),
        # Chave natural por sistema de origem (PNCP, Comprasnet, ...).
        Index("ix_contracts_source_external", "source_system", "external_id", unique=True),
        Index("ix_contracts_uasg", "uasg"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    entity_id: Mapped[int] = mapped_column(ForeignKey("government_entities.id"), nullable=False)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"))
    procurement_id: Mapped[int | None] = mapped_column(ForeignKey("procurements.id"))

    # Proveniência: sistema de origem e identificador externo preservado.
    source_system: Mapped[str] = mapped_column(
        String(20), default="pncp", server_default="pncp", nullable=False
    )
    external_id: Mapped[str | None] = mapped_column(String(64))
    # Unidade Gestora (UASG) e órgão de origem — permitem filtro por campus.
    uasg: Mapped[str | None] = mapped_column(String(20))
    organization_code: Mapped[str | None] = mapped_column(String(20))
    contract_type: Mapped[str | None] = mapped_column(String(60))
    # Valor acumulado (execução), distinto de valor global/contratado.
    accumulated_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))

    pncp_control_number: Mapped[str | None] = mapped_column(String(40))
    year: Mapped[int | None] = mapped_column(Integer)
    sequential: Mapped[int | None] = mapped_column(Integer)
    number: Mapped[str | None] = mapped_column(String(50))
    process_number: Mapped[str | None] = mapped_column(String(80))
    object_description: Mapped[str] = mapped_column(Text, nullable=False)

    initial_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    global_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus, native_enum=False, length=20),
        default=ContractStatus.DESCONHECIDO,
        nullable=False,
    )
    signed_at: Mapped[date | None] = mapped_column(Date)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_until: Mapped[date | None] = mapped_column(Date)

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str | None] = mapped_column(String(600))
    collection_run_id: Mapped[int | None] = mapped_column(ForeignKey("collection_runs.id"))
    search_text: Mapped[str | None] = mapped_column(Text)

    supplier = relationship("Supplier", back_populates="contracts")
    procurement = relationship("Procurement", back_populates="contracts")
    entity = relationship("GovernmentEntity")
    source = relationship("DataSource")
    amendments = relationship(
        "ContractAmendment", back_populates="contract", cascade="all, delete-orphan"
    )


class ContractAmendment(Base, TimestampMixin):
    __tablename__ = "contract_amendments"
    __table_args__ = (Index("ix_contract_amendments_contract", "contract_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False
    )
    term_number: Mapped[str | None] = mapped_column(String(50))
    amendment_type: Mapped[str | None] = mapped_column(String(80))
    value_added: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    value_reduced: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    new_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    new_end_date: Mapped[date | None] = mapped_column(Date)
    signed_at: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(600))

    contract = relationship("Contract", back_populates="amendments")


class Payment(Base, TimestampMixin):
    """Despesa em um estágio financeiro específico (empenho, liquidação, pagamento)."""

    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_contract", "contract_id"),
        Index("ix_payments_stage_date", "stage", "reference_date"),
        Index("ix_payments_entity_stage", "entity_id", "stage"),
        # Idempotência por contrato + identificador externo (ex.: empenho:ID:estagio).
        Index("ix_payments_contract_external", "contract_id", "external_id", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int | None] = mapped_column(ForeignKey("contracts.id"))
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("government_entities.id"))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"))
    stage: Mapped[FinancialStage] = mapped_column(
        Enum(FinancialStage, native_enum=False, length=20), nullable=False
    )
    value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    reference_date: Mapped[date | None] = mapped_column(Date)
    external_id: Mapped[str | None] = mapped_column(String(80))
    # Proveniência e descrição legível (natureza da despesa, nº do documento).
    source_system: Mapped[str] = mapped_column(
        String(20), default="pncp", server_default="pncp", nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(600))
