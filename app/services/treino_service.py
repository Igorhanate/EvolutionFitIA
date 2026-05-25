from datetime import datetime as dt

from sqlalchemy.orm import Session

from app.models.treino import Treino


def _is_real(treino: Treino) -> bool:
    """Treino 'real': cadastrado pelo personal (origem proprio) ou plano completo (>=400 chars)."""
    cont = treino.conteudo if isinstance(treino.conteudo, dict) else {}
    texto = cont.get("texto", "") if isinstance(cont, dict) else ""
    origem = cont.get("origem") if isinstance(cont, dict) else None
    return origem == "proprio" or len(texto or "") >= 400


def listar_treinos(user_id: int, db: Session) -> list[Treino]:
    """Treinos REAIS do usuário, mais recentes primeiro (filtra o lixo histórico)."""
    treinos = (
        db.query(Treino)
        .filter(Treino.user_id == user_id)
        .order_by(Treino.criado_em.desc())
        .all()
    )
    return [t for t in treinos if _is_real(t)]


def cadastrar_treino_proprio(
    user_id: int, nome: str, texto: str, db: Session, exercicios: str = ""
) -> Treino:
    """Persiste um treino externo (origem='proprio'). Não faz commit — o chamador controla."""
    t = Treino(
        user_id=user_id,
        conteudo={
            "texto": texto,
            "nome": nome,
            "exercicios": exercicios,
            "origem": "proprio",
            "gerado_em": dt.utcnow().isoformat(),
        },
    )
    db.add(t)
    db.flush()
    return t


def apagar_treinos(user_id: int, ids: list[int], db: Session) -> int:
    """
    Hard-delete dos treinos cujo id está em `ids` E que pertençam a `user_id`.
    Guarda de segurança única: NUNCA apaga treino de outro usuário, nunca apaga por filtro amplo.
    Não faz commit — o chamador controla a transação. Retorna quantos foram apagados.
    """
    if not ids:
        return 0
    return (
        db.query(Treino)
        .filter(Treino.user_id == user_id, Treino.id.in_(ids))
        .delete(synchronize_session=False)
    )
