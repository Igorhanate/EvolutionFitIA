"""cria tabela alimentos_taco (base nutricional TACO 4a edicao)

Revision ID: 011
Revises: 010
Create Date: 2026-05-26

"""
from alembic import op
import sqlalchemy as sa

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alimentos_taco",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("taco_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("categoria", sa.String(100), nullable=False),
        sa.Column("kcal", sa.Float(), nullable=True),
        sa.Column("proteina_g", sa.Float(), nullable=True),
        sa.Column("lipideos_g", sa.Float(), nullable=True),
        sa.Column("carboidrato_g", sa.Float(), nullable=True),
        sa.Column("fibra_g", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alimentos_taco_taco_id", "alimentos_taco", ["taco_id"])
    op.create_index("ix_alimentos_taco_nome", "alimentos_taco", ["nome"])
    op.create_index("ix_alimentos_taco_categoria", "alimentos_taco", ["categoria"])


def downgrade() -> None:
    op.drop_index("ix_alimentos_taco_categoria", table_name="alimentos_taco")
    op.drop_index("ix_alimentos_taco_nome", table_name="alimentos_taco")
    op.drop_index("ix_alimentos_taco_taco_id", table_name="alimentos_taco")
    op.drop_table("alimentos_taco")
