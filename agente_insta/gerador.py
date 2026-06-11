import os
import sys
import json
import pathlib
from dotenv import load_dotenv
import anthropic

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not API_KEY:
    raise RuntimeError("ANTHROPIC_API_KEY nao encontrada no .env")

MODELO = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
client = anthropic.Anthropic(api_key=API_KEY)

PASTA = pathlib.Path(__file__).parent
SKILL = (PASTA / "SOCIAL_DESIGN_SKILL.md").read_text(encoding="utf-8")

TOOL = {
    "name": "gerar_brief_post",
    "description": "Devolve um brief de post de Instagram pronto pra virar design.",
    "input_schema": {
        "type": "object",
        "properties": {
            "categoria": {"type": "string"},
            "formato": {"type": "string", "enum": ["foto_unica", "carrossel"]},
            "tema": {"type": "string"},
            "gancho": {"type": "string"},
            "slides": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "titulo": {"type": "string"},
                        "apoio": {"type": "string"},
                        "visual": {"type": "string"},
                        "accent": {"type": "boolean"}
                    },
                    "required": ["titulo", "visual"]
                }
            },
            "legenda": {"type": "string", "description": "Use quebras de linha reais, nunca a sequencia \n literal."},
            "hashtags": {"type": "array", "items": {"type": "string"}},
            "obs_visual": {"type": "string"}
        },
        "required": ["categoria", "formato", "tema", "gancho", "slides", "legenda", "hashtags"]
    }
}


def gerar_brief(categoria: str, formato: str, evitar_temas=None) -> dict:
    system = (
        SKILL
        + "\n\n---\nVoce e o gerador de conteudo da Evolution Fit AI. "
        "Crie UM brief de post seguindo TODAS as regras da skill acima. "
        "Na legenda use quebras de linha REAIS, nunca escreva \n. "
        "Responda APENAS chamando a ferramenta gerar_brief_post."
    )
    n = "5 a 7 slides" if formato == "carrossel" else "1 slide (foto unica)"
    user = (
        f"Gere um brief na categoria '{categoria}', formato '{formato}' ({n}). "
        "Conteudo verdadeiro, voz da Evo, portugues do Brasil."
    )
    if evitar_temas:
        user += "\n\nNAO repita estes temas recentes: " + "; ".join(evitar_temas[:30])
    resp = client.messages.create(
        model=MODELO,
        max_tokens=2500,
        system=system,
        tools=[TOOL],
        tool_choice={"type": "tool", "name": "gerar_brief_post"},
        messages=[{"role": "user", "content": user}],
    )
    for bloco in resp.content:
        if bloco.type == "tool_use":
            return bloco.input
    raise RuntimeError("A IA nao retornou o brief esperado.")


if __name__ == "__main__":
    print(f"(modelo: {MODELO})\n")
    print(json.dumps(gerar_brief("informativo", "carrossel"), ensure_ascii=False, indent=2))
