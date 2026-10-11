"""add payment provenance (source_system, description) and idempotency index

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-10-11 12:10:00

Permite armazenar estágios reais de execução (empenhado, liquidado, pago) com
proveniência e reimportação idempotente por (contract_id, external_id).
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "d3e4f5a6b7c8"
down_revision: str | None = "c2d3e4f5a6b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column("source_system", sa.String(length=20), nullable=False, server_default="pncp"),
    )
    op.add_column("payments", sa.Column("description", sa.Text(), nullable=True))
    op.create_index(
        "ix_payments_entity_stage", "payments", ["entity_id", "stage"], unique=False
    )
    op.create_index(
        "ix_payments_contract_external",
        "payments",
        ["contract_id", "external_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_payments_contract_external", table_name="payments")
    op.drop_index("ix_payments_entity_stage", table_name="payments")
    op.drop_column("payments", "description")
    op.drop_column("payments", "source_system")
