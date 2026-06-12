from datetime import date

from sqlalchemy.orm import Session

from app.models.habito_dia import HabitoDia
from app.models.perfil_habitos import PerfilHabitos
from app.models.registro_suplemento import RegistroSuplemento


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _get_or_create_habito_dia(user_id: int, today: date, db: Session) -> HabitoDia:
    habito = (
        db.query(HabitoDia)
        .filter(HabitoDia.user_id == user_id, HabitoDia.data == today)
        .first()
    )
    if not habito:
        habito = HabitoDia(user_id=user_id, data=today, agua_ml=0)
        db.add(habito)
        db.flush()
    return habito


def _get_or_create_perfil(user_id: int, db: Session) -> PerfilHabitos:
    perfil = db.query(PerfilHabitos).filter(PerfilHabitos.user_id == user_id).first()
    if not perfil:
        perfil = PerfilHabitos(user_id=user_id)
        db.add(perfil)
        db.flush()
    return perfil


# ---------------------------------------------------------------------------
# Registro de hábitos
# ---------------------------------------------------------------------------

def registrar_agua(user_id: int, ml: int, db: Session) -> dict:
    habito = _get_or_create_habito_dia(user_id, date.today(), db)
    habito.agua_ml = (habito.agua_ml or 0) + ml
    db.flush()
    return {
        "adicionado_ml": ml,
        "total_ml": habito.agua_ml,
        "total_l": round(habito.agua_ml / 1000, 2),
    }


def registrar_fumou(user_id: int, fumou: bool, db: Session) -> dict:
    habito = _get_or_create_habito_dia(user_id, date.today(), db)
    habito.fumou = fumou
    perfil = _get_or_create_perfil(user_id, db)

    if fumou:
        perfil.streak_inicio_sem_fumar = None
        dias_sem_fumar = 0
    else:
        if not perfil.streak_inicio_sem_fumar:
            perfil.streak_inicio_sem_fumar = date.today()
        dias_sem_fumar = (date.today() - perfil.streak_inicio_sem_fumar).days + 1

    db.flush()
    return {"fumou": fumou, "dias_sem_fumar": dias_sem_fumar}


def registrar_alcool(user_id: int, bebeu: bool, db: Session) -> dict:
    habito = _get_or_create_habito_dia(user_id, date.today(), db)
    habito.bebeu_alcool = bebeu
    perfil = _get_or_create_perfil(user_id, db)

    if bebeu:
        perfil.streak_inicio_sem_alcool = None
        dias_sem_alcool = 0
    else:
        if not perfil.streak_inicio_sem_alcool:
            perfil.streak_inicio_sem_alcool = date.today()
        dias_sem_alcool = (date.today() - perfil.streak_inicio_sem_alcool).days + 1

    db.flush()
    return {"bebeu_alcool": bebeu, "dias_sem_alcool": dias_sem_alcool}


def registrar_suplementos_usuario(user_id: int, suplementos: list[str], db: Session) -> PerfilHabitos:
    perfil = _get_or_create_perfil(user_id, db)
    perfil.suplementos = suplementos
    db.flush()
    return perfil


def registrar_consumo_suplemento(user_id: int, descricao: str, db: Session) -> dict:
    """12-B: registra UM suplemento consumido hoje (texto livre, ex: 'Whey 30g')."""
    hoje = date.today()
    reg = RegistroSuplemento(user_id=user_id, data_consumo=hoje, descricao=descricao.strip())
    db.add(reg)
    db.flush()
    return {"registrado": True, "descricao": descricao.strip(), "data": hoje.isoformat()}


def listar_suplementos_dia(user_id: int, data, db: Session) -> list[RegistroSuplemento]:
    """12.3: suplementos consumidos num dia, ordem cronológica."""
    return (
        db.query(RegistroSuplemento)
        .filter(RegistroSuplemento.user_id == user_id, RegistroSuplemento.data_consumo == data)
        .order_by(RegistroSuplemento.criado_em.asc())
        .all()
    )


def contar_suplementos_dia(user_id: int, data, db: Session) -> int:
    """Resumo do /menu: quantos suplementos foram registrados no dia."""
    return (
        db.query(RegistroSuplemento)
        .filter(RegistroSuplemento.user_id == user_id, RegistroSuplemento.data_consumo == data)
        .count()
    )


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------

def get_resumo_habitos(user_id: int, db: Session) -> dict:
    today = date.today()
    habito = (
        db.query(HabitoDia)
        .filter(HabitoDia.user_id == user_id, HabitoDia.data == today)
        .first()
    )
    perfil = db.query(PerfilHabitos).filter(PerfilHabitos.user_id == user_id).first()

    dias_sem_fumar: int | None = None
    dias_sem_alcool: int | None = None

    if perfil:
        if perfil.streak_inicio_sem_fumar:
            dias_sem_fumar = (today - perfil.streak_inicio_sem_fumar).days + 1
        if perfil.streak_inicio_sem_alcool:
            dias_sem_alcool = (today - perfil.streak_inicio_sem_alcool).days + 1

    agua_ml = habito.agua_ml if habito else 0
    suplementos_hoje_count = (
        db.query(RegistroSuplemento)
        .filter(RegistroSuplemento.user_id == user_id, RegistroSuplemento.data_consumo == today)
        .count()
    )
    return {
        "agua_ml": agua_ml,
        "agua_l": round(agua_ml / 1000, 2),
        "fumou_hoje": habito.fumou if habito else None,
        "bebeu_alcool_hoje": habito.bebeu_alcool if habito else None,
        "suplementos_hoje_count": suplementos_hoje_count,
        "dias_sem_fumar": dias_sem_fumar,
        "dias_sem_alcool": dias_sem_alcool,
        "suplementos_cadastrados": perfil.suplementos if perfil else None,
    }


def precisa_lembrete_suplemento(user_id: int, db: Session) -> bool:
    # 12-B: precisa lembrar se ainda não registrou nenhum suplemento hoje
    tomados_hoje = contar_suplementos_dia(user_id, date.today(), db)
    return tomados_hoje == 0


def listar_suplementos_cadastrados(user_id: int, db: Session) -> list[str]:
    """12-D: lista de suplementos cadastrados (strings 'Nome Dosagem')."""
    perfil = db.query(PerfilHabitos).filter(PerfilHabitos.user_id == user_id).first()
    if not perfil or not perfil.suplementos:
        return []
    return [s for s in perfil.suplementos if isinstance(s, str)]


def adicionar_suplemento_cadastrado(user_id: int, item: str, db: Session) -> list[str]:
    """12-D: adiciona um suplemento (append). Retorna a lista atualizada."""
    perfil = _get_or_create_perfil(user_id, db)
    atual = [s for s in (perfil.suplementos or []) if isinstance(s, str)]
    atual.append(item.strip())
    perfil.suplementos = atual
    db.flush()
    return atual


def remover_suplemento_cadastrado(user_id: int, indice: int, db: Session) -> str | None:
    """12-D: remove por índice (0-based). Retorna o removido ou None."""
    perfil = _get_or_create_perfil(user_id, db)
    atual = [s for s in (perfil.suplementos or []) if isinstance(s, str)]
    if 0 <= indice < len(atual):
        removido = atual.pop(indice)
        perfil.suplementos = atual
        db.flush()
        return removido
    return None


def adicionar_suplementos_lote(user_id: int, items: list[str], db: Session) -> list[str]:
    """12-E: adiciona vários suplementos, ignorando duplicados (case-insensitive).
    Retorna só os que foram realmente adicionados."""
    perfil = _get_or_create_perfil(user_id, db)
    atual = [s for s in (perfil.suplementos or []) if isinstance(s, str)]
    existentes = {s.lower() for s in atual}
    adicionados: list[str] = []
    for it in items:
        it = (it or "").strip()
        if it and it.lower() not in existentes:
            atual.append(it)
            existentes.add(it.lower())
            adicionados.append(it)
    if adicionados:
        perfil.suplementos = atual
        db.flush()
    return adicionados


def get_suplementos_usuario(user_id: int, db: Session) -> list[str] | None:
    perfil = db.query(PerfilHabitos).filter(PerfilHabitos.user_id == user_id).first()
    return perfil.suplementos if perfil else None


def build_habito_context(user_id: int, db: Session) -> str | None:
    resumo = get_resumo_habitos(user_id, db)
    parts = []

    if resumo["agua_ml"] > 0:
        parts.append(f"Água consumida hoje: {resumo['agua_l']}L ({resumo['agua_ml']}ml)")

    if resumo["dias_sem_fumar"] is not None:
        parts.append(f"Streak sem fumar: {resumo['dias_sem_fumar']} dia(s) consecutivos")
    elif resumo["fumou_hoje"] is True:
        parts.append("Fumou hoje — streak sem fumar foi zerado")

    if resumo["dias_sem_alcool"] is not None:
        parts.append(f"Streak sem álcool: {resumo['dias_sem_alcool']} dia(s) consecutivos")
    elif resumo["bebeu_alcool_hoje"] is True:
        parts.append("Bebeu álcool hoje — streak foi zerado")

    if resumo.get("suplementos_hoje_count"):
        parts.append(f"Suplementos tomados hoje: {resumo['suplementos_hoje_count']}")
    elif resumo["suplementos_cadastrados"]:
        nomes = ", ".join(resumo["suplementos_cadastrados"])
        parts.append(f"Suplementos cadastrados: {nomes} (não registrou hoje)")

    if not parts:
        return None

    return "Hábitos de hoje:\n" + "\n".join(f"  • {p}" for p in parts)
