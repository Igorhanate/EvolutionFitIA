"""Perfil de treino por modalidade (tabela perfil_treino_modalidade).

Aditivo ao PerfilFitness: cada modalidade tem seu proprio perfil completo de treino.
Na 1a vez numa modalidade, pre-preenche com os valores do PerfilFitness (usuario so confirma).
"""
import logging

from sqlalchemy.orm import Session

from app.models.perfil_treino_modalidade import PerfilTreinoModalidade
from app.services import perfil_service

logger = logging.getLogger(__name__)

# Campos do perfil por modalidade (os 7 que o usuario confirma/ajusta)
CAMPOS_MODALIDADE = ("local", "objetivo", "dias_semana", "tempo_sessao", "nivel", "lesoes", "horario")

# Mapa: campo da tabela nova -> campo do PerfilFitness (pro pre-preenchimento)
_MAP_DO_PERFIL = {
    "local": "local_treino_padrao",
    "objetivo": "objetivo_padrao",
    "dias_semana": "dias_semana_padrao",
    "tempo_sessao": "tempo_sessao_padrao",
    "nivel": "nivel_experiencia",
    "lesoes": "lesoes",
    "horario": "horario_treino_padrao",
}


def get_perfil_modalidade(user_id: int, modalidade: str, db: Session) -> PerfilTreinoModalidade | None:
    """Retorna o perfil daquela modalidade, ou None se ainda nao existe."""
    if not modalidade:
        return None
    return (
        db.query(PerfilTreinoModalidade)
        .filter(
            PerfilTreinoModalidade.user_id == user_id,
            PerfilTreinoModalidade.modalidade == modalidade,
        )
        .first()
    )


def listar_modalidades_do_user(user_id: int, db: Session) -> list[PerfilTreinoModalidade]:
    """Todos os perfis de modalidade do usuario."""
    return (
        db.query(PerfilTreinoModalidade)
        .filter(PerfilTreinoModalidade.user_id == user_id)
        .order_by(PerfilTreinoModalidade.modalidade.asc())
        .all()
    )


def montar_pre_preenchido(user_id: int, db: Session) -> dict:
    """Monta um dict dos 7 campos a partir do PerfilFitness (pra 1a vez numa modalidade).

    Nao salva nada — so devolve os valores pra mostrar ao usuario confirmar.
    """
    perfil = perfil_service.get_or_create_perfil(user_id, db)
    pre = {}
    for campo_novo, campo_perfil in _MAP_DO_PERFIL.items():
        pre[campo_novo] = getattr(perfil, campo_perfil, None)
    return pre


def criar_ou_atualizar(user_id: int, modalidade: str, campos: dict, db: Session) -> PerfilTreinoModalidade:
    """Cria (ou atualiza) o perfil daquela modalidade com os campos fornecidos.

    `campos` aceita as chaves de CAMPOS_MODALIDADE; chaves desconhecidas sao ignoradas.
    """
    perfil_mod = get_perfil_modalidade(user_id, modalidade, db)
    if perfil_mod is None:
        perfil_mod = PerfilTreinoModalidade(user_id=user_id, modalidade=modalidade)
        db.add(perfil_mod)

    for campo in CAMPOS_MODALIDADE:
        if campo in campos and campos[campo] is not None:
            setattr(perfil_mod, campo, campos[campo])

    db.commit()
    db.refresh(perfil_mod)
    return perfil_mod


def limpar_modalidades_do_user(user_id: int, db: Session) -> int:
    """Apaga todos os perfis de modalidade do usuario (usado no 'limpar meus dados'). Retorna quantos."""
    perfis = listar_modalidades_do_user(user_id, db)
    n = len(perfis)
    for p in perfis:
        db.delete(p)
    db.commit()
    return n
