import sys
import pathlib
from datetime import date
sys.stdout.reconfigure(encoding="utf-8")

from agente_insta.armazenar import listar_hoje


def montar_doc() -> str:
    posts = listar_hoje()
    L = [f"# Briefs Evolution Fit AI - {date.today().isoformat()}", "",
         f"Total: {len(posts)} post(s)", ""]
    for p in posts:
        c = p.conteudo
        slides = c.get("slides", [])
        L += ["---", f"## {c.get('tema','(sem tema)')}",
              f"**Categoria:** {c.get('categoria','')} | **Formato:** {c.get('formato','')} | id={p.id}", "",
              f"**Gancho:** {c.get('gancho','')}", ""]
        if c.get("formato") == "carrossel" or len(slides) > 1:
            L.append("### Slides")
            for i, s in enumerate(slides, 1):
                L.append(f"**Slide {i} - {s.get('titulo','')}**")
                if s.get("apoio"):
                    L.append(f"- Apoio: {s['apoio']}")
                L.append(f"- Visual: {s.get('visual','')}")
                if s.get("accent"):
                    L.append("- (detalhe verde neste slide)")
                L.append("")
        else:
            s = slides[0] if slides else {}
            L += [f"**Arte:** {s.get('titulo','')}"]
            if s.get("apoio"):
                L.append(f"- Apoio: {s['apoio']}")
            L += [f"- Visual: {s.get('visual','')}", ""]
        L += ["**Legenda:**", "```", c.get("legenda", ""), "```", "",
              "**Hashtags:** " + " ".join(c.get("hashtags", []))]
        if c.get("obs_visual"):
            L += ["", f"**Obs visual:** {c['obs_visual']}"]
        L.append("")
    return "\n".join(L)


def salvar_doc() -> str:
    pasta = pathlib.Path(__file__).parent / "brief_aqui"
    pasta.mkdir(parents=True, exist_ok=True)
    nome = f"briefs_{date.today().isoformat()}.md"
    caminho = pasta / nome
    caminho.write_text(montar_doc(), encoding="utf-8")
    return str(caminho)


if __name__ == "__main__":
    print("Doc salvo em:", salvar_doc())
