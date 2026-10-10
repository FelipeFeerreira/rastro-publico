"""Regras de auditoria, achados, evidências e referências de preço."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
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

from app.db.base import Base, JsonType, TimestampMixin
from app.models.enums import FindingRule, FindingSeverity, FindingStatus


class AuditRule(Base, TimestampMixin):
    """Regra determinística e explicável de detecção de anomalias."""

    __tablename__ = "audit_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    rule_type: Mapped[FindingRule | None] = mapped_column(
        Enum(FindingRule, native_enum=False, length=40)
    )
    severity: Mapped[FindingSeverity] = mapped_column(
        Enum(FindingSeverity, native_enum=False, length=20),
        default=FindingSeverity.ATENCAO,
        nullable=False,
    )
    parameters: Mapped[dict | None] = mapped_column(JsonType)
    methodology: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    findings = relationship("AuditFinding", back_populates="rule")


class AuditFinding(Base, TimestampMixin):
    """Achado de auditoria. Indicador para investigação, nunca prova de ilícito."""

    __tablename__ = "audit_findings"
    __table_args__ = (
        Index("ix_audit_findings_rule", "rule_id"),
        Index("ix_audit_findings_status", "status"),
        Index("ix_audit_findings_entity", "entity_id"),
        Index("ix_audit_findings_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    rule_id: Mapped[int] = mapped_column(ForeignKey("audit_rules.id"), nullable=False)
    status: Mapped[FindingStatus] = mapped_column(
        Enum(FindingStatus, native_enum=False, length=30),
        default=FindingStatus.IDENTIFICADO,
        nullable=False,
    )
    severity: Mapped[FindingSeverity] = mapped_column(
        Enum(FindingSeverity, native_enum=False, length=20),
        default=FindingSeverity.ATENCAO,
        nullable=False,
    )

    entity_id: Mapped[int | None] = mapped_column(ForeignKey("government_entities.id"))
    municipality_id: Mapped[int | None] = mapped_column(ForeignKey("municipalities.id"))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"))
    procurement_id: Mapped[int | None] = mapped_column(ForeignKey("procurements.id"))
    contract_id: Mapped[int | None] = mapped_column(ForeignKey("contracts.id"))

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text)
    methodology: Mapped[str | None] = mapped_column(Text)
    limitations: Mapped[str | None] = mapped_column(Text)

    # Valores calculados pelo motor determinístico (nunca pela IA).
    metrics: Mapped[dict | None] = mapped_column(JsonType)
    # Referências às evidências e aos registros oficiais de origem.
    evidence: Mapped[list | None] = mapped_column(JsonType)
    source_records: Mapped[list | None] = mapped_column(JsonType)
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    data_quality_notes: Mapped[str | None] = mapped_column(Text)

    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    review_history: Mapped[list | None] = mapped_column(JsonType)

    rule = relationship("AuditRule", back_populates="findings")


class PriceReference(Base, TimestampMixin):
    """Preço de referência calculado para itens comparáveis."""

    __tablename__ = "price_references"
    __table_args__ = (
        Index("ix_price_references_category", "category_key"),
        Index("ix_price_references_period", "reference_year", "reference_month"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category_key: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(60))
    reference_year: Mapped[int | None] = mapped_column(Integer)
    reference_month: Mapped[int | None] = mapped_column(Integer)
    median_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    p25_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    p75_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    min_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    max_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    sample_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    methodology: Mapped[str | None] = mapped_column(Text)
    computed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
