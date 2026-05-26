"""
Lê Taco-4a-Edicao.xlsx, aplica tratamento de sujeira e gera:
  - scripts/taco_seed.json   (lista de alimentos prontos para inserção)

Script standalone: não importa nada de app.* e não toca em banco.
Rode na raiz do projeto:
    python scripts/importar_taco.py
"""

import json
import os
import sys

import pandas as pd

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCEL_PATH = os.path.join(ROOT, "Taco-4a-Edicao.xlsx")
SEED_PATH = os.path.join(ROOT, "scripts", "taco_seed.json")

# ---------------------------------------------------------------------------
# Heurística de detecção de linha-separador de categoria
#
# O Excel tem a planilha diagramada para impressão em folhas A4, o que cria
# três tipos de linhas não-alimento intercaladas nos dados:
#
#   (A) Linha vazia          — col0 == 'nan'
#   (B) Cabeçalho repetido   — col0 in {'número do', 'alimento'} (repete o
#                              cabeçalho de cada folha)
#   (C) Linha de categoria   — col0 = nome do grupo (ex: "Cereais e derivados")
#   (D) Rodapé/legenda       — col0 in {'legenda'} ou col0 formado só por
#                              símbolos '*†‡§' (notas de rodapé ao final)
#
# Regra: se col0 não é conversível para inteiro, não se enquadra em (A/B/D)
# → é uma linha de categoria (C). Validado empiricamente: produz exatamente
# 15 categorias correspondentes às 15 da TACO 4ª Ed.
# ---------------------------------------------------------------------------
SKIP_COL0 = {"nan", "legenda", "alimento"}
SKIP_COL0_PREFIXES = ("número",)
LEGEND_SYMBOLS = set("*†‡§")


def is_category_row(c0: str) -> bool:
    c0l = c0.lower()
    if c0l in SKIP_COL0:
        return False
    for prefix in SKIP_COL0_PREFIXES:
        if c0l.startswith(prefix):
            return False
    if c0 and all(ch in LEGEND_SYMBOLS for ch in c0):
        return False
    return True


# ---------------------------------------------------------------------------
# Tratamento de valores numéricos com sujeira
# ---------------------------------------------------------------------------
def parse_macro(raw: str, field: str, stats: dict, alimento_nome: str, taco_id: int):
    """
    Retorna float ou None após aplicar as regras de limpeza TACO:
      "Tr"  → 0.0   (traços: abaixo do limite de detecção)
      "*"   → None  (dado não disponível — NUNCA inventar)
      NaN   → None  (análise não solicitada)
      negativo → 0.0 (artefato de arredondamento laboratorial; apenas carboidrato)
    """
    v = raw.strip()
    if v == "" or v == "nan":
        return None
    if v == "Tr":
        stats["tr"][field] = stats["tr"].get(field, 0) + 1
        return 0.0
    if v == "*":
        stats["asterisk"][field] = stats["asterisk"].get(field, 0) + 1
        return None
    try:
        num = float(v)
    except ValueError:
        # Valor desconhecido — tratar como None e registrar aviso
        stats["unknown"].append({"field": field, "value": v, "taco_id": taco_id, "nome": alimento_nome})
        return None

    if num < 0:
        stats["negative"].append({
            "field": field,
            "taco_id": taco_id,
            "nome": alimento_nome,
            "valor_original": num,
        })
        return 0.0
    return num


# ---------------------------------------------------------------------------
# Leitura e parsing
# ---------------------------------------------------------------------------
def parse_excel():
    df = pd.read_excel(EXCEL_PATH, sheet_name="CMVCol taco3", header=None, dtype=str)

    stats = {
        "tr": {},           # {"campo": contagem}
        "asterisk": {},     # {"campo": contagem}
        "negative": [],     # lista de {field, taco_id, nome, valor_original}
        "unknown": [],      # valores inesperados
        "leading_space": [], # nomes com espaço no início (antes do strip)
    }

    alimentos = []
    categoria_atual = None
    categorias_ordem = []

    for i in range(3, len(df)):
        c0_raw = str(df.iloc[i, 0])
        c0 = c0_raw.strip()

        # --- Linha vazia ---
        if c0 == "nan":
            continue

        # --- Tentar parsear como ID de alimento ---
        try:
            taco_id = int(float(c0))
        except (ValueError, TypeError):
            # Não é número → pode ser categoria ou lixo de cabeçalho/rodapé
            if is_category_row(c0):
                categoria_atual = c0
                if c0 not in categorias_ordem:
                    categorias_ordem.append(c0)
            continue

        # --- Linha de alimento ---
        nome_raw = str(df.iloc[i, 1])
        if nome_raw.strip() == "nan":
            continue  # linha sem nome: ignorar

        # Detectar espaço no início (antes do strip)
        if nome_raw != nome_raw.lstrip():
            stats["leading_space"].append({"taco_id": taco_id, "nome_original": nome_raw})

        nome = nome_raw.strip()

        # Campos numéricos
        kcal          = parse_macro(str(df.iloc[i, 3]), "kcal",          stats, nome, taco_id)
        proteina_g    = parse_macro(str(df.iloc[i, 5]), "proteina_g",    stats, nome, taco_id)
        lipideos_g    = parse_macro(str(df.iloc[i, 6]), "lipideos_g",    stats, nome, taco_id)
        carboidrato_g = parse_macro(str(df.iloc[i, 8]), "carboidrato_g", stats, nome, taco_id)
        fibra_g       = parse_macro(str(df.iloc[i, 9]), "fibra_g",       stats, nome, taco_id)

        alimentos.append({
            "taco_id":       taco_id,
            "nome":          nome,
            "categoria":     categoria_atual,
            "kcal":          kcal,
            "proteina_g":    proteina_g,
            "lipideos_g":    lipideos_g,
            "carboidrato_g": carboidrato_g,
            "fibra_g":       fibra_g,
        })

    return alimentos, categorias_ordem, stats


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------
def imprimir_relatorio(alimentos, categorias_ordem, stats):
    print("=" * 64)
    print("RELATÓRIO DE PARSING — BASE TACO 4ª EDIÇÃO")
    print("=" * 64)

    print(f"\nTotal de alimentos parseados : {len(alimentos)}")
    print(f"Total de categorias distintas: {len(categorias_ordem)}")
    print("\nCategorias (ordem encontrada):")
    for i, cat in enumerate(categorias_ordem, 1):
        print(f"  {i:>2}. {cat}")

    print("\n--- Tr → 0.0 (por campo) ---")
    if stats["tr"]:
        for campo, cnt in sorted(stats["tr"].items()):
            print(f"  {campo:<20}: {cnt}")
    else:
        print("  (nenhum)")

    print("\n--- * → None (por campo) ---")
    if stats["asterisk"]:
        for campo, cnt in sorted(stats["asterisk"].items()):
            print(f"  {campo:<20}: {cnt}")
    else:
        print("  (nenhum)")

    print("\n--- Carboidrato negativo → 0.0 ---")
    neg = [x for x in stats["negative"] if x["field"] == "carboidrato_g"]
    print(f"  Ocorrências: {len(neg)}")
    for item in neg:
        print(f"  taco_id={item['taco_id']:>3}  valor_original={item['valor_original']:>8.5f}  nome={item['nome']}")

    fibra_none = sum(1 for a in alimentos if a["fibra_g"] is None)
    pct_fibra = fibra_none / len(alimentos) * 100 if alimentos else 0
    print(f"\n--- fibra_g = None ---")
    print(f"  {fibra_none} alimentos ({pct_fibra:.1f}%)")

    kcal_none = [a for a in alimentos if a["kcal"] is None]
    print(f"\n--- kcal = None ({len(kcal_none)} alimentos) ---")
    for a in kcal_none:
        print(f"  taco_id={a['taco_id']:>3}  {a['nome']}")

    print("\n--- Nomes com espaço no início (antes do strip) ---")
    if stats["leading_space"]:
        for item in stats["leading_space"]:
            print(f"  taco_id={item['taco_id']:>3}  nome_original={repr(item['nome_original'])}")
    else:
        print("  (nenhum)")

    if stats["unknown"]:
        print("\n--- AVISO: valores inesperados ---")
        for item in stats["unknown"]:
            print(f"  {item}")

    print("\n--- Amostra: 3 primeiros alimentos ---")
    for a in alimentos[:3]:
        print(f"  {json.dumps(a, ensure_ascii=False)}")

    print("\n--- Amostra: 3 últimos alimentos ---")
    for a in alimentos[-3:]:
        print(f"  {json.dumps(a, ensure_ascii=False)}")

    print("\n" + "=" * 64)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    if not os.path.exists(EXCEL_PATH):
        print(f"ERRO: arquivo não encontrado: {EXCEL_PATH}", file=sys.stderr)
        sys.exit(1)

    print(f"Lendo {EXCEL_PATH} ...", flush=True)
    alimentos, categorias_ordem, stats = parse_excel()

    with open(SEED_PATH, "w", encoding="utf-8") as f:
        json.dump(alimentos, f, ensure_ascii=False, indent=2)
    print(f"Seed gerado: {SEED_PATH} ({len(alimentos)} registros)\n", flush=True)

    imprimir_relatorio(alimentos, categorias_ordem, stats)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
