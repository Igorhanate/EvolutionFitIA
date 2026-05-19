"""add ultima_mensagem_id to usuarios

Revision ID: 002
Revises: 001
Create Date: 2026-05-18

"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usuarios",
        sa.Column("ultima_mensagem_id", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("usuarios", "ultima_mensagem_id")
