"""add medidas_corporais and fotos_composicao

Revision ID: 004
Revises: 003
Create Date: 2026-05-19

"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "medidas_corporais",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("data_medicao", sa.Date(), nullable=False),
        sa.Column("peso_kg", sa.Float(), nullable=True),
        sa.Column("cintura_cm", sa.Float(), nullable=True),
        sa.Column("quadril_cm", sa.Float(), nullable=True),
        sa.Column("pescoco_cm", sa.Float(), nullable=True),
        sa.Column("braco_cm", sa.Float(), nullable=True),
        sa.Column("coxa_cm", sa.Float(), nullable=True),
        sa.Column("panturrilha_cm", sa.Float(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_medidas_corporais_user_id", "medidas_corporais", ["user_id"])

    op.create_table(
        "fotos_composicao",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("gordura_estimada_pct", sa.Float(), nullable=True),
        sa.Column("analise_texto", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fotos_composicao_user_id", "fotos_composicao", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_fotos_composicao_user_id", "fotos_composicao")
    op.drop_table("fotos_composicao")
    op.drop_index("ix_medidas_corporais_user_id", "medidas_corporais")
    op.drop_table("medidas_corporais")
