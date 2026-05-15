"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telefone", sa.String(length=20), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telefone"),
    )
    op.create_index("ix_usuarios_telefone", "usuarios", ["telefone"])

    op.create_table(
        "assinaturas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "plano",
            sa.Enum("trimestral", "anual", name="plano_enum"),
            nullable=False,
        ),
        sa.Column("data_inicio", sa.Date(), nullable=False),
        sa.Column("data_fim", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("ativo", "expirado", "cancelado", name="status_assinatura_enum"),
            nullable=False,
            server_default="ativo",
        ),
        sa.Column("hotmart_transaction_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hotmart_transaction_id"),
    )
    op.create_index("ix_assinaturas_user_id", "assinaturas", ["user_id"])

    op.create_table(
        "treinos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("conteudo", sa.JSON(), nullable=False),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_treinos_user_id", "treinos", ["user_id"])

    op.create_table(
        "dietas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("conteudo", sa.JSON(), nullable=False),
        sa.Column("criado_em", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dietas_user_id", "dietas", ["user_id"])

    op.create_table(
        "conversas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("mensagens", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("atualizado_em", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("conversas")
    op.drop_index("ix_dietas_user_id", "dietas")
    op.drop_table("dietas")
    op.drop_index("ix_treinos_user_id", "treinos")
    op.drop_table("treinos")
    op.drop_index("ix_assinaturas_user_id", "assinaturas")
    op.drop_table("assinaturas")
    op.drop_index("ix_usuarios_telefone", "usuarios")
    op.drop_table("usuarios")
    op.execute("DROP TYPE IF EXISTS plano_enum")
    op.execute("DROP TYPE IF EXISTS status_assinatura_enum")
