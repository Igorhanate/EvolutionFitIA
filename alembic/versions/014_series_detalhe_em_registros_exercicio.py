"""adiciona series_detalhe (JSON) em registros_exercicio

Revision ID: 014
Revises: 013
Create Date: 2026-05-31

"""
from alembic import op
import sqlalchemy as sa

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("registros_exercicio", sa.Column("series_detalhe", sa.JSON, nullable=True))


def downgrade() -> None:
    op.drop_column("registros_exercicio", "series_detalhe")
