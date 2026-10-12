"""add enrichment columns to municipal_expenses

Revision ID: f5a6b7c8d9e0
Revises: 26675963e6d6
Create Date: 2026-10-12 11:00:00

Guarda os campos oficiais de detalhe do TCE-SP (histórico, descrição da ação,
função de governo, elemento de despesa, fonte, URL do detalhe e status de
enriquecimento), preservando os valores financeiros existentes.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "f5a6b7c8d9e0"
down_revision: str | None = "26675963e6d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = [
    ("detail_id", sa.String(length=40)),
    ("detail_url", sa.String(length=300)),
    ("history", sa.Text()),
    ("activity_description", sa.Text()),
    ("government_function", sa.String(length=120)),
    ("government_subfunction", sa.String(length=120)),
    ("expense_element", sa.String(length=220)),
    ("funding_source", sa.String(length=120)),
    ("enrichment_status", sa.String(length=20)),
    ("enriched_at", sa.DateTime(timezone=True)),
]


def upgrade() -> None:
    for name, column_type in _COLUMNS:
        op.add_column("municipal_expenses", sa.Column(name, column_type, nullable=True))
    op.create_index(
        "ix_municipal_expenses_enrichment_status",
        "municipal_expenses",
        ["enrichment_status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_municipal_expenses_enrichment_status", table_name="municipal_expenses")
    for name, _ in reversed(_COLUMNS):
        op.drop_column("municipal_expenses", name)
