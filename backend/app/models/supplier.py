"""Fornecedores / empresas contratadas."""

from __future__ import annotations

from sqlalchemy import Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Supplier(Base, TimestampMixin):
    """Fornecedor identificado por documento (CNPJ/CPF).

    Nota de privacidade (LGPD): a plataforma apresenta apenas dados de pessoas
    jurídicas e de agentes públicos no exercício de função pública. CPF é
    armazenado apenas quando estritamente necessário e exibido de forma
    mascarada nas interfaces públicas.
    """

    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("document", name="uq_suppliers_document"),
        Index("ix_suppliers_name", "name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document: Mapped[str] = mapped_column(String(14), nullable=False, index=True)
    document_type: Mapped[str | None] = mapped_column(String(4))  # PJ | PF | PE
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    trade_name: Mapped[str | None] = mapped_column(String(300))
    legal_nature: Mapped[str | None] = mapped_column(String(200))
    is_individual: Mapped[bool] = mapped_column(default=False, nullable=False)
    search_text: Mapped[str | None] = mapped_column(Text)

    contracts = relationship("Contract", back_populates="supplier")
    procurements_won = relationship("ProcurementResult", back_populates="supplier")
