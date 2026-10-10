"""Agentes públicos, cargos e remunerações (dados quando legalmente disponíveis).

A coleta e a exibição de dados pessoais observam a LGPD e o interesse público,
apresentando apenas o necessário (nome, cargo, órgão, remuneração pública).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class PublicPerson(Base, TimestampMixin):
    __tablename__ = "public_people"
    __table_args__ = (Index("ix_public_people_name", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    # Documento mascarado (ex.: ***.123.456-**) quando aplicável.
    masked_document: Mapped[str | None] = mapped_column(String(40))
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("government_entities.id"))
    role_title: Mapped[str | None] = mapped_column(String(200))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"))
    source_url: Mapped[str | None] = mapped_column(String(600))
    search_text: Mapped[str | None] = mapped_column(Text)

    remunerations = relationship("Remuneration", back_populates="person")


class PublicPosition(Base, TimestampMixin):
    __tablename__ = "public_positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("government_entities.id"))
    organization: Mapped[str | None] = mapped_column(String(300))
    reference_salary: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))


class Remuneration(Base, TimestampMixin):
    __tablename__ = "remunerations"
    __table_args__ = (Index("ix_remunerations_person_period", "person_id", "reference_year", "reference_month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(
        ForeignKey("public_people.id", ondelete="CASCADE"), nullable=False
    )
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("government_entities.id"))
    reference_year: Mapped[int | None] = mapped_column(Integer)
    reference_month: Mapped[int | None] = mapped_column(Integer)
    gross_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    net_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    deductions: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    reference_date: Mapped[date | None] = mapped_column(Date)
    source_url: Mapped[str | None] = mapped_column(String(600))

    person = relationship("PublicPerson", back_populates="remunerations")
