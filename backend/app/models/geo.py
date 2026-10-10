"""Estados, municípios e órgãos/entidades governamentais."""

from __future__ import annotations

from sqlalchemy import (
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import GovernmentPower, GovernmentSphere


class State(Base, TimestampMixin):
    __tablename__ = "states"

    id: Mapped[int] = mapped_column(primary_key=True)
    ibge_code: Mapped[str] = mapped_column(String(2), unique=True, nullable=False)
    uf: Mapped[str] = mapped_column(String(2), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    municipalities = relationship("Municipality", back_populates="state")


class Municipality(Base, TimestampMixin):
    __tablename__ = "municipalities"
    __table_args__ = (Index("ix_municipalities_state_name", "state_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    ibge_code: Mapped[str] = mapped_column(String(7), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    state_id: Mapped[int] = mapped_column(ForeignKey("states.id"), nullable=False)
    search_text: Mapped[str | None] = mapped_column(Text)

    state = relationship("State", back_populates="municipalities")
    entities = relationship("GovernmentEntity", back_populates="municipality")


class GovernmentEntity(Base, TimestampMixin):
    """Órgão/entidade público. Chave natural: CNPJ (quando disponível)."""

    __tablename__ = "government_entities"
    __table_args__ = (
        UniqueConstraint("cnpj", name="uq_government_entities_cnpj"),
        Index("ix_government_entities_sphere_power", "sphere", "power"),
        Index("ix_government_entities_name", "name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cnpj: Mapped[str | None] = mapped_column(String(14), index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    acronym: Mapped[str | None] = mapped_column(String(50))
    sphere: Mapped[GovernmentSphere] = mapped_column(
        Enum(GovernmentSphere, native_enum=False, length=20),
        default=GovernmentSphere.OTHER,
        nullable=False,
    )
    power: Mapped[GovernmentPower] = mapped_column(
        Enum(GovernmentPower, native_enum=False, length=20),
        default=GovernmentPower.OTHER,
        nullable=False,
    )
    state_id: Mapped[int | None] = mapped_column(ForeignKey("states.id"))
    municipality_id: Mapped[int | None] = mapped_column(ForeignKey("municipalities.id"))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"))
    source_url: Mapped[str | None] = mapped_column(String(600))
    search_text: Mapped[str | None] = mapped_column(Text)

    municipality = relationship("Municipality", back_populates="entities")
    state = relationship("State")
    procurements = relationship("Procurement", back_populates="entity")
