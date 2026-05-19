"""add registros_exercicio and estado_pendente

Revision ID: 003
Revises: 002
Create Date: 2026-05-19

"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "registros_exercicio",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("sessao_data", sa.Date(), nullable=False),
        sa.Column("posicao_sessao", sa.Integer(), nullable=False),
        sa.Column("exercicio", sa.String(200), nullable=False),
        sa.Column("exercicio_display", sa.String(200), nullable=False),
        sa.Column("series", sa.Integer(), nullable=False),
        sa.Column("repeticoes", sa.Integer(), nullable=False),
        sa.Column("carga_kg", sa.Float(), nullable=False),
        sa.Column("rm_estimado", sa.Float(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_registros_exercicio_user_id", "registros_exercicio", ["user_id"])
    op.create_index(
        "ix_registros_exercicio_user_exercicio",
        "registros_exercicio",
        ["user_id", "exercicio"],
    )

    op.add_column("conversas", sa.Column("estado_pendente", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("conversas", "estado_pendente")
    op.drop_index("ix_registros_exercicio_user_exercicio", "registros_exercicio")
    op.drop_index("ix_registros_exercicio_user_id", "registros_exercicio")
    op.drop_table("registros_exercicio")
