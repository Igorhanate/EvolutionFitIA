"""cria tabela lembretes_remedio

Revision ID: 016
Revises: 015
Create Date: 2026-06-14

"""
from alembic import op
import sqlalchemy as sa

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lembretes_remedio",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(100), nullable=False),
        sa.Column("nome_norm", sa.String(100), nullable=False),
        sa.Column("quantidade", sa.String(50), nullable=True),
        sa.Column("intervalo_horas", sa.Integer(), nullable=False),
        sa.Column("proximo_em", sa.DateTime(), nullable=False),
        sa.Column("fim_em", sa.DateTime(), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("terminado_em", sa.DateTime(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"]),
    )
    op.create_index("ix_lembretes_remedio_user_id", "lembretes_remedio", ["user_id"])
    op.create_index("ix_lembretes_remedio_nome_norm", "lembretes_remedio", ["nome_norm"])
    op.create_index("ix_lembretes_remedio_proximo_em", "lembretes_remedio", ["proximo_em"])


def downgrade() -> None:
    op.drop_index("ix_lembretes_remedio_proximo_em", table_name="lembretes_remedio")
    op.drop_index("ix_lembretes_remedio_nome_norm", table_name="lembretes_remedio")
    op.drop_index("ix_lembretes_remedio_user_id", table_name="lembretes_remedio")
    op.drop_table("lembretes_remedio")
