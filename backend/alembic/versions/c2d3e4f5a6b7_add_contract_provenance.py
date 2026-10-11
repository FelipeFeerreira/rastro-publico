"""add contract provenance (source_system, external_id, uasg) and entity uasg

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-10-11 11:40:00

Adaptações necessárias para importar contratos do Comprasnet (federal) preservando
proveniência e permitindo filtro confiável por campus/UASG, mantendo os contratos
do PNCP existentes (source_system='pncp', external_id nulo).
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "c2d3e4f5a6b7"
down_revision: str | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "contracts",
        sa.Column("source_system", sa.String(length=20), nullable=False, server_default="pncp"),
    )
    op.add_column("contracts", sa.Column("external_id", sa.String(length=64), nullable=True))
    op.add_column("contracts", sa.Column("uasg", sa.String(length=20), nullable=True))
    op.add_column("contracts", sa.Column("organization_code", sa.String(length=20), nullable=True))
    op.add_column("contracts", sa.Column("contract_type", sa.String(length=60), nullable=True))
    op.add_column("contracts", sa.Column("accumulated_value", sa.Numeric(18, 2), nullable=True))
    op.create_index("ix_contracts_uasg", "contracts", ["uasg"], unique=False)
    op.create_index(
        "ix_contracts_source_external",
        "contracts",
        ["source_system", "external_id"],
        unique=True,
    )

    op.add_column("government_entities", sa.Column("uasg", sa.String(length=20), nullable=True))
    op.create_index(
        "ix_government_entities_uasg", "government_entities", ["uasg"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_government_entities_uasg", table_name="government_entities")
    op.drop_column("government_entities", "uasg")

    op.drop_index("ix_contracts_source_external", table_name="contracts")
    op.drop_index("ix_contracts_uasg", table_name="contracts")
    op.drop_column("contracts", "accumulated_value")
    op.drop_column("contracts", "contract_type")
    op.drop_column("contracts", "organization_code")
    op.drop_column("contracts", "uasg")
    op.drop_column("contracts", "external_id")
    op.drop_column("contracts", "source_system")
