"""cria tabela sessoes_treino e adiciona treino_nome em registros_exercicio

Revision ID: 013
Revises: 012
Create Date: 2026-05-31

"""
from alembic import op
import sqlalchemy as sa

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sessoes_treino",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("treino_nome", sa.String(100), nullable=False),
        sa.Column("iniciada_em", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("finalizada_em", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"]),
    )
    op.create_index("ix_sessoes_treino_user_id", "sessoes_treino", ["user_id"])

    op.add_column("registros_exercicio", sa.Column("treino_nome", sa.String(100), nullable=True))
    op.create_index("ix_registros_exercicio_treino_nome", "registros_exercicio", ["treino_nome"])


def downgrade() -> None:
    op.drop_index("ix_registros_exercicio_treino_nome", table_name="registros_exercicio")
    op.drop_column("registros_exercicio", "treino_nome")

    op.drop_index("ix_sessoes_treino_user_id", table_name="sessoes_treino")
    op.drop_table("sessoes_treino")
