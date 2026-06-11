"""cria tabela registros_suplemento

Revision ID: 015
Revises: 014
Create Date: 2026-06-09

"""
from alembic import op
import sqlalchemy as sa

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "registros_suplemento",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("data_consumo", sa.Date(), nullable=False),
        sa.Column("descricao", sa.String(200), nullable=False),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"]),
    )
    op.create_index("ix_registros_suplemento_user_id", "registros_suplemento", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_registros_suplemento_user_id", table_name="registros_suplemento")
    op.drop_table("registros_suplemento")
