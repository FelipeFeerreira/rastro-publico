"""Modelos ORM do Rastro Público.

Importados aqui para garantir que `Base.metadata` inclua todas as tabelas
(necessário para Alembic e para criação de schema em testes).
"""

from app.models.audit import AuditFinding, AuditRule, PriceReference
from app.models.enums import (  # noqa: F401
    CollectionStatus,
    ContractStatus,
    EvidenceKind,
    FinancialStage,
    FindingRule,
    FindingSeverity,
    FindingStatus,
    GovernmentPower,
    GovernmentSphere,
    InvestigationStatus,
    ItemKind,
    MunicipalExpenseStage,
    NotificationChannel,
    ProcurementModality,
    ProcurementStatus,
    SourceStatus,
    SubscriptionKind,
    UserRole,
)
from app.models.geo import GovernmentEntity, Municipality, State
from app.models.investigation import (
    Document,
    Investigation,
    InvestigationEvidence,
    MonitoringSubscription,
    Notification,
)
from app.models.municipal import MunicipalExpense
from app.models.person import PublicPerson, PublicPosition, Remuneration
from app.models.procurement import (
    Contract,
    ContractAmendment,
    Payment,
    Procurement,
    ProcurementItem,
    ProcurementResult,
)
from app.models.source import CollectionRun, DataSource
from app.models.supplier import Supplier
from app.models.user import AuditLog, User, UserRoleAssignment

__all__ = [
    "AuditFinding",
    "AuditLog",
    "AuditRule",
    "CollectionRun",
    "Contract",
    "ContractAmendment",
    "DataSource",
    "Document",
    "GovernmentEntity",
    "Investigation",
    "InvestigationEvidence",
    "MonitoringSubscription",
    "MunicipalExpense",
    "Municipality",
    "Notification",
    "Payment",
    "PriceReference",
    "Procurement",
    "ProcurementItem",
    "ProcurementResult",
    "PublicPerson",
    "PublicPosition",
    "Remuneration",
    "State",
    "Supplier",
    "User",
    "UserRoleAssignment",
]
