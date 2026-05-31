from datetime import datetime

from sqlalchemy.orm import Session

from app.models.sessao_treino import SessaoTreino


def get_sessao_ativa(user_id: int, db: Session) -> SessaoTreino | None:
    """Retorna a SessaoTreino mais recente com finalizada_em=None, ou None."""
    return (
        db.query(SessaoTreino)
        .filter(SessaoTreino.user_id == user_id, SessaoTreino.finalizada_em.is_(None))
        .order_by(SessaoTreino.iniciada_em.desc())
        .first()
    )


def iniciar_sessao(user_id: int, treino_nome: str, db: Session) -> SessaoTreino:
    """Cria sessão nova. Se houver uma ativa, fecha automaticamente (finalizada_em=now) antes."""
    ativa = get_sessao_ativa(user_id, db)
    if ativa is not None:
        ativa.finalizada_em = datetime.utcnow()
        db.flush()
    nova = SessaoTreino(user_id=user_id, treino_nome=treino_nome.strip())
    db.add(nova)
    db.flush()
    return nova
