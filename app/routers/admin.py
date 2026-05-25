import json
import os
import tempfile
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import require_admin_key
from app.models.assinatura import Assinatura
from app.models.conversa import Conversa
from app.models.dieta import Dieta
from app.models.foto_composicao import FotoComposicao
from app.models.medida_corporal import MedidaCorporal
from app.models.registro_exercicio import RegistroExercicio
from app.models.meta_nutricional import MetaNutricional
from app.models.registro_refeicao import RegistroRefeicao
from app.models.treino import Treino
from app.models.usuario import Usuario
from app.services import exercicio_service, nutricao_service, treino_service
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


@router.get("/users/{user_id}/meta-nutricional")
def get_meta_nutricional(user_id: int, db: Session = Depends(get_db)):
    """Meta nutricional ativa e histórico de metas do usuário."""
    _get_user_or_404(user_id, db)
    metas = (
        db.query(MetaNutricional)
        .filter(MetaNutricional.user_id == user_id)
        .order_by(MetaNutricional.criado_em.desc())
        .all()
    )
    return [
        {
            "id": m.id,
            "nome": m.nome,
            "calorias_alvo": m.calorias_alvo,
            "proteinas_alvo_g": m.proteinas_alvo_g,
            "carboidratos_alvo_g": m.carboidratos_alvo_g,
            "gorduras_alvo_g": m.gorduras_alvo_g,
            "ativa": m.ativa,
            "criado_em": m.criado_em.isoformat(),
        }
        for m in metas
    ]


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


@router.post("/subscriptions/grant", summary="Concede assinatura manual a um número")
def grant_subscription(
    telefone: str = Query(..., description="Número no formato 5511999999999"),
    plano: str = Query("anual", description="trimestral ou anual"),
    dias: int = Query(365, description="Duração em dias"),
    db: Session = Depends(get_db),
):
    if plano not in ("trimestral", "anual"):
        raise HTTPException(status_code=400, detail="plano deve ser 'trimestral' ou 'anual'")
    user = db.query(Usuario).filter(Usuario.telefone == telefone).first()
    if not user:
        user = Usuario(telefone=telefone)
        db.add(user)
        db.flush()
    hoje = date.today()
    sub = Assinatura(
        user_id=user.id,
        plano=plano,
        data_inicio=hoje,
        data_fim=hoje + timedelta(days=dias),
        status="ativo",
        hotmart_transaction_id=f"manual-{telefone}-{hoje}",
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return {
        "ok": True,
        "user_id": user.id,
        "telefone": user.telefone,
        "plano": sub.plano,
        "data_inicio": sub.data_inicio.isoformat(),
        "data_fim": sub.data_fim.isoformat(),
        "status": sub.status,
    }


class DeleteTreinosRequest(BaseModel):
    user_id: int
    ids: list[int]
    dry_run: bool = True


def _treino_preview(t: Treino, n: int = 150) -> dict:
    cont = t.conteudo if isinstance(t.conteudo, dict) else {}
    texto = cont.get("texto", "") if isinstance(cont, dict) else str(t.conteudo)
    return {
        "id": t.id,
        "criado_em": t.criado_em.isoformat() if t.criado_em else None,
        "texto_preview": (texto or "")[:n],
    }


@router.post("/treinos/delete", summary="Deleta treinos por lista explícita de IDs (dry-run por padrão)")
def delete_treinos(payload: DeleteTreinosRequest, db: Session = Depends(get_db)):
    """
    Deleção SEGURA de treinos. Proteções:
    - Só apaga treinos cujo id está EXPLICITAMENTE em `ids` (nunca por filtro/heurística).
    - Só apaga treinos que pertençam a `user_id` (ids de outro usuário são ignorados e reportados).
    - `dry_run` é TRUE por padrão: nesse modo nada é apagado, só retorna o preview para revisão.
    - Em `dry_run=false`, faz BACKUP do conteúdo completo ANTES de apagar.
    - Lista de ids vazia => no-op.
    """
    # Segurança (5): lista vazia => não faz nada
    if not payload.ids:
        return {
            "dry_run": payload.dry_run,
            "user_id": payload.user_id,
            "message": "Lista de ids vazia — nenhuma ação tomada.",
            "encontrados": [],
            "nao_encontrados": [],
            "total": 0,
        }

    # Garante que o usuário existe
    _get_user_or_404(payload.user_id, db)

    # Segurança (5 e 6): só treinos cujo id está na lista E que pertençam ao user_id
    treinos = (
        db.query(Treino)
        .filter(Treino.user_id == payload.user_id, Treino.id.in_(payload.ids))
        .order_by(Treino.criado_em.desc())
        .all()
    )
    encontrados_ids = {t.id for t in treinos}
    # ids pedidos que não existem OU não pertencem a esse usuário (ignorados)
    nao_encontrados = [i for i in payload.ids if i not in encontrados_ids]

    # MODO DRY-RUN (3) — padrão: NÃO apaga nada
    if payload.dry_run:
        return {
            "dry_run": True,
            "user_id": payload.user_id,
            "seriam_apagados": len(treinos),
            "encontrados": [_treino_preview(t) for t in treinos],
            "nao_encontrados": nao_encontrados,
        }

    # MODO REAL (4) — só com dry_run=false explícito
    # 4.1 BACKUP do conteúdo completo ANTES de apagar
    backup = [
        {
            "id": t.id,
            "user_id": t.user_id,
            "conteudo": t.conteudo,
            "criado_em": t.criado_em.isoformat() if t.criado_em else None,
        }
        for t in treinos
    ]
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup_path = os.path.join(
        tempfile.gettempdir(), f"backup_treinos_deletados_{timestamp}.json"
    )
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=2)

    # 4.2 SÓ DEPOIS do backup, apaga — apenas os ids encontrados desse usuário
    ids_a_apagar = sorted(encontrados_ids)
    apagados = treino_service.apagar_treinos(payload.user_id, ids_a_apagar, db)
    db.commit()

    return {
        "dry_run": False,
        "user_id": payload.user_id,
        "total_apagados": apagados,
        "ids_apagados": ids_a_apagar,
        "nao_encontrados": nao_encontrados,
        "backup_path": backup_path,
        # Backup também no corpo: o disco do Render é efêmero (some em restart/redeploy),
        # então retornamos o conteúdo aqui para você capturar imediatamente.
        "backup": backup,
    }


def _get_user_or_404(user_id: int, db: Session) -> Usuario:
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user
