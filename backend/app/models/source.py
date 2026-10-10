"""Fontes de dados públicos e histórico de sincronização."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, JsonType, TimestampMixin
from app.models.enums import CollectionStatus, SourceStatus


class DataSource(Base, TimestampMixin):
    """Catálogo de fontes oficiais integradas (PNCP, Portal da Transparência...)."""

    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    homepage_url: Mapped[str] = mapped_column(String(500), nullable=False)
    api_documentation_url: Mapped[str | None] = mapped_column(String(500))
    license_name: Mapped[str | None] = mapped_column(String(200))
    license_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[SourceStatus] = mapped_column(
        Enum(SourceStatus, native_enum=False, length=20),
        default=SourceStatus.ACTIVE,
        nullable=False,
    )
    requires_authentication: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    coverage_description: Mapped[str | None] = mapped_column(Text)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    collection_runs = relationship("CollectionRun", back_populates="source")


class CollectionRun(Base, TimestampMixin):
    """Cada execução de sincronização de uma fonte, com log e métricas."""

    __tablename__ = "collection_runs"
    __table_args__ = (
        Index("ix_collection_runs_source_started", "source_id", "started_at"),
        Index("ix_collection_runs_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[CollectionStatus] = mapped_column(
        Enum(CollectionStatus, native_enum=False, length=20),
        default=CollectionStatus.RUNNING,
        nullable=False,
    )
    scope: Mapped[str | None] = mapped_column(String(200))
    parameters: Mapped[dict | None] = mapped_column(JsonType)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    records_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_log: Mapped[list | None] = mapped_column(JsonType)
    message: Mapped[str | None] = mapped_column(Text)

    source = relationship("DataSource", back_populates="collection_runs")
