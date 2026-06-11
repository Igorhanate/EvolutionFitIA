from datetime import date, timedelta
from agente_insta.db import SessionLocal
from agente_insta.modelos import PostGerado


def _normalizar(brief: dict) -> dict:
    leg = brief.get("legenda")
    if isinstance(leg, str):
        brief["legenda"] = leg.replace("\n", "\n")
    return brief


def salvar_brief(brief: dict) -> int:
    brief = _normalizar(brief)
    with SessionLocal() as s:
        post = PostGerado(
            data_geracao=date.today(),
            categoria=brief.get("categoria", ""),
            formato=brief.get("formato", ""),
            tema=brief.get("tema", ""),
            conteudo=brief,
            status="novo",
        )
        s.add(post)
        s.commit()
        s.refresh(post)
        return post.id


def temas_recentes(dias: int = 14):
    limite = date.today() - timedelta(days=dias)
    with SessionLocal() as s:
        rows = s.query(PostGerado.tema).filter(PostGerado.data_geracao >= limite).all()
    return [r[0] for r in rows]


def listar_hoje():
    with SessionLocal() as s:
        return (
            s.query(PostGerado)
            .filter(PostGerado.data_geracao == date.today())
            .order_by(PostGerado.id)
            .all()
        )
