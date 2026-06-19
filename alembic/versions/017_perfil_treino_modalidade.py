"""cria tabela perfil_treino_modalidade

Revision ID: 017
Revises: 016
Create Date: 2026-06-15

"""
from alembic import op
import sqlalchemy as sa

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "perfil_treino_modalidade",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("modalidade", sa.String(30), nullable=False),
        sa.Column("local", sa.String(30), nullable=True),
        sa.Column("objetivo", sa.String(30), nullable=True),
        sa.Column("dias_semana", sa.String(10), nullable=True),
        sa.Column("tempo_sessao", sa.String(20), nullable=True),
        sa.Column("nivel", sa.String(20), nullable=True),
        sa.Column("lesoes", sa.Text(), nullable=True),
        sa.Column("horario", sa.String(20), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("atualizado_em", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"]),
        sa.UniqueConstraint("user_id", "modalidade", name="uq_perfil_treino_user_modalidade"),
    )
    op.create_index("ix_perfil_treino_modalidade_user_id", "perfil_treino_modalidade", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_perfil_treino_modalidade_user_id", table_name="perfil_treino_modalidade")
    op.drop_table("perfil_treino_modalidade")
