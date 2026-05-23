"""add dias_semana_padrao e tempo_sessao_padrao a perfis_fitness

Revision ID: 009
Revises: 008
Create Date: 2026-05-23

"""
from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("perfis_fitness", sa.Column("dias_semana_padrao", sa.String(10), nullable=True))
    op.add_column("perfis_fitness", sa.Column("tempo_sessao_padrao", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("perfis_fitness", "tempo_sessao_padrao")
    op.drop_column("perfis_fitness", "dias_semana_padrao")
