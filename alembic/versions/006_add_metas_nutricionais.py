"""add metas_nutricionais

Revision ID: 006
Revises: 005
Create Date: 2026-05-19

"""
from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "metas_nutricionais",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("texto_original", sa.Text(), nullable=True),
        sa.Column("calorias_alvo", sa.Integer(), nullable=False),
        sa.Column("proteinas_alvo_g", sa.Float(), nullable=True),
        sa.Column("carboidratos_alvo_g", sa.Float(), nullable=True),
        sa.Column("gorduras_alvo_g", sa.Float(), nullable=True),
        sa.Column("ativa", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_metas_nutricionais_user_id", "metas_nutricionais", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_metas_nutricionais_user_id", "metas_nutricionais")
    op.drop_table("metas_nutricionais")
