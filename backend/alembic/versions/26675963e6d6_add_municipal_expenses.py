"""add municipal expenses

Revision ID: 26675963e6d6
Revises: d3e4f5a6b7c8
Create Date: 2026-10-11 15:36:01.314894

Cria a tabela de despesas municipais (eventos financeiros do TCE-SP), separada
das contratações e dos pagamentos federais. Os índices de busca (FTS/trgm) e a
constraint de UASG das tabelas existentes foram mantidos intactos.
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "26675963e6d6"
down_revision: str | None = "d3e4f5a6b7c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "municipal_expenses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("municipality_id", sa.Integer(), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("supplier_name", sa.String(length=300), nullable=True),
        sa.Column("supplier_document", sa.String(length=14), nullable=True),
        sa.Column("supplier_raw_id", sa.String(length=140), nullable=True),
        sa.Column("empenho_number", sa.String(length=60), nullable=True),
        sa.Column(
            "stage",
            sa.Enum(
                "EMPENHADO",
                "LIQUIDADO",
                "PAGO",
                "REFORCO",
                "ANULACAO",
                name="municipalexpensestage",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("value", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("event_year", sa.Integer(), nullable=True),
        sa.Column("event_month", sa.Integer(), nullable=True),
        sa.Column("month_name", sa.String(length=20), nullable=True),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("external_key", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.String(length=600), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["entity_id"],
            ["government_entities.id"],
            name=op.f("fk_municipal_expenses_entity_id_government_entities"),
        ),
        sa.ForeignKeyConstraint(
            ["municipality_id"],
            ["municipalities.id"],
            name=op.f("fk_municipal_expenses_municipality_id_municipalities"),
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["data_sources.id"],
            name=op.f("fk_municipal_expenses_source_id_data_sources"),
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name=op.f("fk_municipal_expenses_supplier_id_suppliers"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_municipal_expenses")),
        sa.UniqueConstraint(
            "source_id", "external_key", name="uq_municipal_expenses_source_key"
        ),
    )
    op.create_index(
        "ix_municipal_expenses_entity", "municipal_expenses", ["entity_id"], unique=False
    )
    op.create_index(
        "ix_municipal_expenses_muni_period",
        "municipal_expenses",
        ["municipality_id", "event_year", "event_month"],
        unique=False,
    )
    op.create_index(
        "ix_municipal_expenses_stage", "municipal_expenses", ["stage"], unique=False
    )
    op.create_index(
        "ix_municipal_expenses_supplier", "municipal_expenses", ["supplier_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_municipal_expenses_supplier", table_name="municipal_expenses")
    op.drop_index("ix_municipal_expenses_stage", table_name="municipal_expenses")
    op.drop_index("ix_municipal_expenses_muni_period", table_name="municipal_expenses")
    op.drop_index("ix_municipal_expenses_entity", table_name="municipal_expenses")
    op.drop_table("municipal_expenses")
