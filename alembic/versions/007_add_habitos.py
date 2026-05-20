"""add habitos_dia e perfis_habitos

Revision ID: 007
Revises: 006
Create Date: 2026-05-19

"""
from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "habitos_dia",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("agua_ml", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("fumou", sa.Boolean(), nullable=True),
        sa.Column("bebeu_alcool", sa.Boolean(), nullable=True),
        sa.Column("suplementos_tomados", sa.Boolean(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "data", name="uq_habito_dia_user_data"),
    )
    op.create_index("ix_habitos_dia_user_id", "habitos_dia", ["user_id"])

    op.create_table(
        "perfis_habitos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("suplementos", sa.JSON(), nullable=True),
        sa.Column("streak_inicio_sem_fumar", sa.Date(), nullable=True),
        sa.Column("streak_inicio_sem_alcool", sa.Date(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_perfis_habitos_user"),
    )


def downgrade() -> None:
    op.drop_table("perfis_habitos")
    op.drop_index("ix_habitos_dia_user_id", "habitos_dia")
    op.drop_table("habitos_dia")
