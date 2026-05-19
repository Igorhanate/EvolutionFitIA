from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.conversa import Conversa
from app.models.dieta import Dieta
from app.models.treino import Treino
from app.models.usuario import Usuario
from app.schemas.assinatura import AssinaturaRead
from app.schemas.usuario import UsuarioRead
from app.services.subscription_service import activate_subscription, check_active_subscription

router = APIRouter(tags=["Admin"])


@router.post("/activate-test")
def activate_test_subscription(phone: str, plano: str = "anual", db: Session = Depends(get_db)):
    """Ativa assinatura de teste para um número de telefone (apenas para desenvolvimento)."""
    user = activate_subscription(
        phone=phone,
        nome="Teste",
        email=None,
        plano=plano,
        transaction_id=f"TEST-{phone}",
        db=db,
    )
    return {"status": "ok", "user_id": user.id, "telefone": user.telefone, "plano": plano}


@router.get("/users", response_model=list[dict])
def list_users(db: Session = Depends(get_db)):
    users = db.query(Usuario).order_by(Usuario.created_at.desc()).all()
    result = []
    for user in users:
        assinatura = check_active_subscription(user.id, db)
        result.append({
            "id": user.id,
            "telefone": user.telefone,
            "nome": user.nome,
            "email": user.email,
            "created_at": user.created_at.isoformat(),
            "assinatura_ativa": assinatura is not None,
            "plano": assinatura.plano if assinatura else None,
            "data_fim": assinatura.data_fim.isoformat() if assinatura else None,
        })
    return result


@router.get("/users/{user_id}/treinos")
def get_treinos(user_id: int, db: Session = Depends(get_db)):
    _get_user_or_404(user_id, db)
    treinos = db.query(Treino).filter(Treino.user_id == user_id).order_by(Treino.criado_em.desc()).all()
    return [{"id": t.id, "conteudo": t.conteudo, "criado_em": t.criado_em.isoformat()} for t in treinos]


@router.get("/users/{user_id}/dietas")
def get_dietas(user_id: int, db: Session = Depends(get_db)):
    _get_user_or_404(user_id, db)
    dietas = db.query(Dieta).filter(Dieta.user_id == user_id).order_by(Dieta.criado_em.desc()).all()
    return [{"id": d.id, "conteudo": d.conteudo, "criado_em": d.criado_em.isoformat()} for d in dietas]


@router.get("/users/{user_id}/conversa")
def get_conversa(user_id: int, db: Session = Depends(get_db)):
    _get_user_or_404(user_id, db)
    conversa = db.query(Conversa).filter(Conversa.user_id == user_id).first()
    if not conversa:
        return {"mensagens": []}
    return {"mensagens": conversa.mensagens, "atualizado_em": conversa.atualizado_em.isoformat()}


def _get_user_or_404(user_id: int, db: Session) -> Usuario:
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user
