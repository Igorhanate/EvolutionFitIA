from datetime import date

from sqlalchemy.orm import Session

from app.models.habito_dia import HabitoDia
from app.models.perfil_habitos import PerfilHabitos


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


def registrar_tomei_suplementos(user_id: int, db: Session) -> dict:
    habito = _get_or_create_habito_dia(user_id, date.today(), db)
    habito.suplementos_tomados = True
    db.flush()
    return {"registrado": True, "data": date.today().isoformat()}


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
    return {
        "agua_ml": agua_ml,
        "agua_l": round(agua_ml / 1000, 2),
        "fumou_hoje": habito.fumou if habito else None,
        "bebeu_alcool_hoje": habito.bebeu_alcool if habito else None,
        "suplementos_tomados_hoje": habito.suplementos_tomados if habito else None,
        "dias_sem_fumar": dias_sem_fumar,
        "dias_sem_alcool": dias_sem_alcool,
        "suplementos_cadastrados": perfil.suplementos if perfil else None,
    }


def precisa_lembrete_suplemento(user_id: int, db: Session) -> bool:
    habito = (
        db.query(HabitoDia)
        .filter(HabitoDia.user_id == user_id, HabitoDia.data == date.today())
        .first()
    )
    return not (habito and habito.suplementos_tomados)


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

    if resumo["suplementos_tomados_hoje"] is True:
        parts.append("Suplementos do dia: ✅ registrados como tomados")
    elif resumo["suplementos_cadastrados"]:
        nomes = ", ".join(resumo["suplementos_cadastrados"])
        parts.append(f"Suplementos cadastrados: {nomes} (não registrou hoje)")

    if not parts:
        return None

    return "Hábitos de hoje:\n" + "\n".join(f"  • {p}" for p in parts)
