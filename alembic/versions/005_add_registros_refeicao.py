"""add registros_refeicao

Revision ID: 005
Revises: 004
Create Date: 2026-05-19

"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "registros_refeicao",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("data_refeicao", sa.Date(), nullable=False),
        sa.Column("descricao", sa.String(500), nullable=False),
        sa.Column("calorias_kcal", sa.Integer(), nullable=True),
        sa.Column("proteinas_g", sa.Float(), nullable=True),
        sa.Column("carboidratos_g", sa.Float(), nullable=True),
        sa.Column("gorduras_g", sa.Float(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_registros_refeicao_user_id", "registros_refeicao", ["user_id"])
    op.create_index(
        "ix_registros_refeicao_user_data",
        "registros_refeicao",
        ["user_id", "data_refeicao"],
    )


def downgrade() -> None:
    op.drop_index("ix_registros_refeicao_user_data", "registros_refeicao")
    op.drop_index("ix_registros_refeicao_user_id", "registros_refeicao")
    op.drop_table("registros_refeicao")
