"""add perfis_fitness

Revision ID: 008
Revises: 007
Create Date: 2026-05-23

"""
from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "perfis_fitness",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        # Campos estáveis
        sa.Column("sexo", sa.String(1), nullable=True),
        sa.Column("data_nascimento", sa.Date(), nullable=True),
        sa.Column("altura_cm", sa.SmallInteger(), nullable=True),
        # Campos variáveis (confirmados a cada treino/dieta)
        sa.Column("peso_kg", sa.Numeric(5, 1), nullable=True),
        sa.Column("nivel_experiencia", sa.String(20), nullable=True),
        sa.Column("lesoes", sa.Text(), nullable=True),
        sa.Column("objetivo_padrao", sa.String(30), nullable=True),
        # Preferências de treino
        sa.Column("tipo_treino_padrao", sa.String(30), nullable=True),
        sa.Column("local_treino_padrao", sa.String(30), nullable=True),
        sa.Column("horario_treino_padrao", sa.String(20), nullable=True),
        # Específicos de dieta
        sa.Column("restricoes_alimentares", sa.Text(), nullable=True),
        sa.Column("orcamento_alimentar", sa.String(10), nullable=True),
        sa.Column("tempo_cozinhar", sa.String(15), nullable=True),
        # Timestamps
        sa.Column("criado_em", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_perfis_fitness_user"),
    )
    op.create_index("ix_perfis_fitness_user_id", "perfis_fitness", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_perfis_fitness_user_id", "perfis_fitness")
    op.drop_table("perfis_fitness")
