from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import require_admin_key
from app.models.conversa import Conversa
from app.models.dieta import Dieta
from app.models.foto_composicao import FotoComposicao
from app.models.medida_corporal import MedidaCorporal
from app.models.registro_exercicio import RegistroExercicio
from app.models.registro_refeicao import RegistroRefeicao
from app.models.treino import Treino
from app.models.usuario import Usuario
from app.services import exercicio_service, nutricao_service
from app.services.subscription_service import check_active_subscription

router = APIRouter(tags=["Admin"], dependencies=[Depends(require_admin_key)])


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


@router.get("/users/{user_id}/evolucao/sessao")
def get_evolucao_sessao(user_id: int, db: Session = Depends(get_db)):
    """Soma de 1RMs por sessão — curva de performance geral."""
    _get_user_or_404(user_id, db)
    return exercicio_service.get_evolucao_sessao(user_id, db)


@router.get("/users/{user_id}/evolucao/exercicio")
def get_evolucao_exercicio(
    user_id: int,
    exercicio: str = Query(..., description="Nome do exercício"),
    posicao: int | None = Query(None, description="Filtrar por posição na sessão"),
    db: Session = Depends(get_db),
):
    """
    Série temporal de 1RM para um exercício específico.
    Com `posicao`, compara apenas sessões onde o exercício estava nessa posição.
    """
    _get_user_or_404(user_id, db)
    return exercicio_service.get_evolucao_exercicio(user_id, exercicio, posicao, db)


@router.get("/users/{user_id}/exercicios")
def list_exercicios(user_id: int, db: Session = Depends(get_db)):
    """Lista todos os exercícios já registrados pelo usuário (únicos)."""
    _get_user_or_404(user_id, db)
    rows = (
        db.query(
            RegistroExercicio.exercicio,
            RegistroExercicio.exercicio_display,
        )
        .filter(RegistroExercicio.user_id == user_id)
        .distinct()
        .order_by(RegistroExercicio.exercicio)
        .all()
    )
    return [{"exercicio": r.exercicio, "exercicio_display": r.exercicio_display} for r in rows]


@router.get("/users/{user_id}/medidas")
def get_medidas(user_id: int, db: Session = Depends(get_db)):
    """Histórico de medidas corporais do usuário."""
    _get_user_or_404(user_id, db)
    medidas = nutricao_service.get_historico_medidas(user_id, db, limite=50)
    return [
        {
            "id": m.id,
            "data_medicao": m.data_medicao.isoformat(),
            "peso_kg": m.peso_kg,
            "cintura_cm": m.cintura_cm,
            "quadril_cm": m.quadril_cm,
            "pescoco_cm": m.pescoco_cm,
            "braco_cm": m.braco_cm,
            "coxa_cm": m.coxa_cm,
            "panturrilha_cm": m.panturrilha_cm,
            "criado_em": m.criado_em.isoformat(),
        }
        for m in medidas
    ]


@router.get("/users/{user_id}/refeicoes")
def get_refeicoes(
    user_id: int,
    data: str | None = Query(None, description="Filtrar por data (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """Histórico de refeições registradas pelo usuário."""
    _get_user_or_404(user_id, db)
    q = db.query(RegistroRefeicao).filter(RegistroRefeicao.user_id == user_id)
    if data:
        from datetime import date as date_type
        q = q.filter(RegistroRefeicao.data_refeicao == date_type.fromisoformat(data))
    refeicoes = q.order_by(RegistroRefeicao.criado_em.desc()).all()
    return [
        {
            "id": r.id,
            "data_refeicao": r.data_refeicao.isoformat(),
            "descricao": r.descricao,
            "calorias_kcal": r.calorias_kcal,
            "proteinas_g": r.proteinas_g,
            "carboidratos_g": r.carboidratos_g,
            "gorduras_g": r.gorduras_g,
            "criado_em": r.criado_em.isoformat(),
        }
        for r in refeicoes
    ]


@router.get("/users/{user_id}/fotos")
def get_fotos(user_id: int, db: Session = Depends(get_db)):
    """Histórico de análises de composição corporal por foto."""
    _get_user_or_404(user_id, db)
    fotos = (
        db.query(FotoComposicao)
        .filter(FotoComposicao.user_id == user_id)
        .order_by(FotoComposicao.criado_em.desc())
        .all()
    )
    return [
        {
            "id": f.id,
            "gordura_estimada_pct": f.gordura_estimada_pct,
            "analise_texto": f.analise_texto,
            "criado_em": f.criado_em.isoformat(),
        }
        for f in fotos
    ]


def _get_user_or_404(user_id: int, db: Session) -> Usuario:
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user
