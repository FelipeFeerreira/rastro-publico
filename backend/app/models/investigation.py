"""Investigações, evidências, documentos, monitoramento e notificações."""

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
from app.models.enums import (
    EvidenceKind,
    InvestigationStatus,
    NotificationChannel,
    SubscriptionKind,
)


class Investigation(Base, TimestampMixin):
    """Espaço de investigação privado de um usuário."""

    __tablename__ = "investigations"
    __table_args__ = (Index("ix_investigations_owner", "owner_user_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[InvestigationStatus] = mapped_column(
        Enum(InvestigationStatus, native_enum=False, length=20),
        default=InvestigationStatus.ABERTA,
        nullable=False,
    )
    # Metadados do escopo: entidades, período, tema.
    scope: Mapped[dict | None] = mapped_column(JsonType)
    tags: Mapped[list | None] = mapped_column(JsonType)
    is_private: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    owner = relationship("User", back_populates="investigations")
    evidence_items = relationship(
        "InvestigationEvidence", back_populates="investigation", cascade="all, delete-orphan"
    )


class InvestigationEvidence(Base, TimestampMixin):
    __tablename__ = "investigation_evidence"
    __table_args__ = (Index("ix_investigation_evidence_investigation", "investigation_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    investigation_id: Mapped[int] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[EvidenceKind] = mapped_column(
        Enum(EvidenceKind, native_enum=False, length=20), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    # Referências a registros públicos (procurement_id, contract_id, finding_id...).
    reference_type: Mapped[str | None] = mapped_column(String(60))
    reference_id: Mapped[str | None] = mapped_column(String(80))
    source_url: Mapped[str | None] = mapped_column(String(600))
    payload: Mapped[dict | None] = mapped_column(JsonType)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"))

    investigation = relationship("Investigation", back_populates="evidence_items")


class Document(Base, TimestampMixin):
    """Documento oficial referenciado ou armazenado (S3-compatível)."""

    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_source", "source_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"))
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    document_type: Mapped[str | None] = mapped_column(String(80))
    source_url: Mapped[str | None] = mapped_column(String(800))
    storage_key: Mapped[str | None] = mapped_column(String(500))
    checksum: Mapped[str | None] = mapped_column(String(128))
    content_type: Mapped[str | None] = mapped_column(String(120))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Relacionamento polimórfico leve com o registro de origem.
    related_type: Mapped[str | None] = mapped_column(String(60))
    related_id: Mapped[str | None] = mapped_column(String(80))
    extracted_text: Mapped[str | None] = mapped_column(Text)


class MonitoringSubscription(Base, TimestampMixin):
    __tablename__ = "monitoring_subscriptions"
    __table_args__ = (Index("ix_monitoring_user", "user_id", "is_active"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[SubscriptionKind] = mapped_column(
        Enum(SubscriptionKind, native_enum=False, length=30), nullable=False
    )
    target_reference: Mapped[str] = mapped_column(String(120), nullable=False)
    label: Mapped[str] = mapped_column(String(300), nullable=False)
    filters: Mapped[dict | None] = mapped_column(JsonType)
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, native_enum=False, length=20),
        default=NotificationChannel.IN_APP,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user = relationship("User", back_populates="subscriptions")
    notifications = relationship("Notification", back_populates="subscription")


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_read", "user_id", "is_read"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("monitoring_subscriptions.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str | None] = mapped_column(String(600))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JsonType)

    user = relationship("User", back_populates="notifications")
    subscription = relationship("MonitoringSubscription", back_populates="notifications")
