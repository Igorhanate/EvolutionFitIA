import sys
import json
sys.stdout.reconfigure(encoding="utf-8")

from agente_insta.gerador import gerar_brief
from agente_insta.armazenar import salvar_brief, listar_hoje

if __name__ == "__main__":
    brief = gerar_brief("curiosidade", "foto_unica")
    pid = salvar_brief(brief)
    print(f"Salvo com id={pid}")
    posts = listar_hoje()
    print(f"Posts de hoje no banco: {len(posts)}\n")
    print(json.dumps(posts[-1].conteudo, ensure_ascii=False, indent=2))
