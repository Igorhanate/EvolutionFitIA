"""seed alimentos_taco com base TACO 4a edicao (597 alimentos)

Revision ID: 012
Revises: 011
Create Date: 2026-05-26

"""
import json
from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------------
# Resolução de caminho — crítico para rodar local E no Docker do Render.
#
# __file__ = <raiz>/alembic/versions/012_seed_alimentos_taco.py
#   .parent  → <raiz>/alembic/versions/
#   .parent  → <raiz>/alembic/
#   .parent  → <raiz>/           ← raiz do projeto
#
# Nunca usamos cwd() nem caminhos relativos ao diretório de trabalho.
# ---------------------------------------------------------------------------
_SEED_PATH = Path(__file__).resolve().parent.parent.parent / "scripts" / "taco_seed.json"

# Definição leve da tabela para op.bulk_insert.
# Inclui apenas as colunas que o seed fornece; 'id' é omitido (autoincrement).
# op.bulk_insert é preferido a op.get_bind().execute() porque:
#   - é a API idiomática do Alembic para carga em bulk;
#   - funciona nos modos online e offline;
#   - Python None nos dicts é mapeado automaticamente para SQL NULL.
_alimentos_taco = sa.table(
    "alimentos_taco",
    sa.column("taco_id",       sa.Integer),
    sa.column("nome",          sa.String),
    sa.column("categoria",     sa.String),
    sa.column("kcal",          sa.Float),
    sa.column("proteina_g",    sa.Float),
    sa.column("lipideos_g",    sa.Float),
    sa.column("carboidrato_g", sa.Float),
    sa.column("fibra_g",       sa.Float),
)


def upgrade() -> None:
    with open(_SEED_PATH, encoding="utf-8") as f:
        registros = json.load(f)

    # Idempotência: limpa antes de inserir para que re-rodar nunca duplique.
    op.execute(sa.text("DELETE FROM alimentos_taco"))

    op.bulk_insert(_alimentos_taco, registros)

    print(f"[012] {len(registros)} alimentos inseridos em alimentos_taco.")


def downgrade() -> None:
    # Esvazia os dados; a tabela em si é dropada pela migração 011.
    op.execute(sa.text("DELETE FROM alimentos_taco"))
    print("[012] downgrade: alimentos_taco esvaziada.")
