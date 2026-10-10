"""add item category_key for price comparability

Revision ID: b1c2d3e4f5a6
Revises: 8a2efe8fb454
Create Date: 2026-10-10 16:40:00
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "8a2efe8fb454"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "procurement_items", sa.Column("category_key", sa.String(length=120), nullable=True)
    )
    op.create_index(
        "ix_procurement_items_category_key",
        "procurement_items",
        ["category_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_procurement_items_category_key", table_name="procurement_items")
    op.drop_column("procurement_items", "category_key")
