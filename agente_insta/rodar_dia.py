import sys
sys.stdout.reconfigure(encoding="utf-8")

from agente_insta.runner import gerar_lote
from agente_insta.armazenar import listar_hoje
from agente_insta.entrega import salvar_doc

if __name__ == "__main__":
    print("Gerando os posts do dia...\n")
    for pid, cat, fmt, tema in gerar_lote():
        print(f"  id={pid} | {cat} | {fmt} | {tema}")
    print(f"\nTotal de hoje: {len(listar_hoje())}")
    print("Doc salvo em:", salvar_doc())
