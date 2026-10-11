"""Despesas municipais (eventos financeiros) — fonte TCE-SP.

Fica **separado** das contratações e dos pagamentos federais (Comprasnet).
Cada linha é um *evento* de despesa (empenho, liquidação, pagamento, reforço ou
anulação) e não um contrato. Nunca criamos vínculo com contratos.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import MunicipalExpenseStage


class MunicipalExpense(Base, TimestampMixin):
    __tablename__ = "municipal_expenses"
    __table_args__ = (
        # Idempotência: mesma origem + chave natural do evento não duplica.
        UniqueConstraint("source_id", "external_key", name="uq_municipal_expenses_source_key"),
        Index("ix_municipal_expenses_muni_period", "municipality_id", "event_year", "event_month"),
        Index("ix_municipal_expenses_entity", "entity_id"),
        Index("ix_municipal_expenses_supplier", "supplier_id"),
        Index("ix_municipal_expenses_stage", "stage"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), nullable=False)
    municipality_id: Mapped[int] = mapped_column(
        ForeignKey("municipalities.id"), nullable=False
    )
    # Instituição responsável (Prefeitura, Câmara, autarquia).
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("government_entities.id"))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"))

    supplier_name: Mapped[str | None] = mapped_column(String(300))
    supplier_document: Mapped[str | None] = mapped_column(String(14))
    supplier_raw_id: Mapped[str | None] = mapped_column(String(140))

    empenho_number: Mapped[str | None] = mapped_column(String(60))
    stage: Mapped[MunicipalExpenseStage] = mapped_column(
        Enum(MunicipalExpenseStage, native_enum=False, length=20), nullable=False
    )
    # Valor como publicado. Ausente permanece NULL (nunca 0 por padrão).
    value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))

    event_year: Mapped[int | None] = mapped_column(Integer)
    event_month: Mapped[int | None] = mapped_column(Integer)
    month_name: Mapped[str | None] = mapped_column(String(20))
    event_date: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)

    external_key: Mapped[str] = mapped_column(String(64), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(600))
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    municipality = relationship("Municipality")
    entity = relationship("GovernmentEntity")
    supplier = relationship("Supplier")
