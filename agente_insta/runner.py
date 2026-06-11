import sys
import random
sys.stdout.reconfigure(encoding="utf-8")

from agente_insta.gerador import gerar_brief
from agente_insta.armazenar import salvar_brief, temas_recentes, listar_hoje

CATEGORIAS = ["curiosidade", "informativo", "antes_depois", "divulgacao", "dieta", "treino", "apelativo"]
PESOS =      [3,             3,            2,              2,             3,        3,         1]
FORMATOS = ["foto_unica", "carrossel"]


def sortear_combos(qtd: int):
    combos, usadas = [], []
    for _ in range(qtd):
        cat = random.choices(CATEGORIAS, weights=PESOS, k=1)[0]
        t = 0
        while cat in usadas and t < 5:
            cat = random.choices(CATEGORIAS, weights=PESOS, k=1)[0]
            t += 1
        usadas.append(cat)
        combos.append((cat, random.choice(FORMATOS)))
    return combos


def gerar_lote(qtd=None):
    if qtd is None:
        qtd = random.choice([2, 3])
    evitar = temas_recentes(14)
    resultado = []
    for cat, fmt in sortear_combos(qtd):
        brief = gerar_brief(cat, fmt, evitar_temas=evitar)
        pid = salvar_brief(brief)
        evitar.append(brief.get("tema", ""))
        resultado.append((pid, cat, fmt, brief.get("tema", "")))
    return resultado


if __name__ == "__main__":
    print("Gerando lote do dia...\n")
    for pid, cat, fmt, tema in gerar_lote():
        print(f"  id={pid} | {cat} | {fmt} | {tema}")
    print(f"\nTotal de hoje no banco: {len(listar_hoje())}")
