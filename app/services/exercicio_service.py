from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.registro_exercicio import RegistroExercicio

VARIACAO_ANORMAL_PCT = 0.20  # 20%


def normalizar_nome(nome: str) -> str:
    return nome.strip().lower()


# ---------------------------------------------------------------------------
# Cálculo de 1RM
# ---------------------------------------------------------------------------

def calcular_rm(carga: float, reps: int) -> dict | None:
    """
    Calcula 1RM estimado pelas fórmulas aplicáveis ao range de repetições.

    3–5 reps  → Epley + Brzycki (média)
    6–10 reps → Lander
    Fora desse range → None (sem cálculo confiável)
    """
    if reps < 3 or reps > 10:
        return None

    resultados: dict[str, float] = {}

    if 3 <= reps <= 5:
        resultados["epley"] = round(carga * (1 + reps / 30), 1)
        resultados["brzycki"] = round(carga / (1.0278 - 0.0278 * reps), 1)

    if 6 <= reps <= 10:
        resultados["lander"] = round((100 * carga) / (101.3 - 2.67123 * reps), 1)

    if not resultados:
        return None

    media = round(sum(resultados.values()) / len(resultados), 1)
    return {**resultados, "media": media}


# ---------------------------------------------------------------------------
# Sessão
# ---------------------------------------------------------------------------

def get_proxima_posicao(user_id: int, sessao_data: date, db: Session) -> int:
    count = (
        db.query(func.count(RegistroExercicio.id))
        .filter(
            RegistroExercicio.user_id == user_id,
            RegistroExercicio.sessao_data == sessao_data,
        )
        .scalar()
    )
    return (count or 0) + 1


def get_registros_sessao(user_id: int, sessao_data: date, db: Session) -> list[RegistroExercicio]:
    return (
        db.query(RegistroExercicio)
        .filter(
            RegistroExercicio.user_id == user_id,
            RegistroExercicio.sessao_data == sessao_data,
        )
        .order_by(RegistroExercicio.posicao_sessao)
        .all()
    )


# ---------------------------------------------------------------------------
# Histórico por exercício + posição
# ---------------------------------------------------------------------------

def get_historico_exercicio(
    user_id: int,
    exercicio_norm: str,
    posicao: int,
    db: Session,
    limite: int = 5,
) -> list[RegistroExercicio]:
    """
    Retorna até `limite` registros anteriores do exercício NA MESMA POSIÇÃO da sessão.
    Somente compara quando o exercício ocupou a mesma posição em ambas as sessões.
    """
    return (
        db.query(RegistroExercicio)
        .filter(
            RegistroExercicio.user_id == user_id,
            RegistroExercicio.exercicio == exercicio_norm,
            RegistroExercicio.posicao_sessao == posicao,
        )
        .order_by(RegistroExercicio.sessao_data.desc())
        .limit(limite)
        .all()
    )


# ---------------------------------------------------------------------------
# Validação de variação
# ---------------------------------------------------------------------------

def detectar_variacao_anormal(
    carga_nova: float, historico: list[RegistroExercicio]
) -> tuple[bool, float | None]:
    """Retorna (anormal, variacao_pct). anormal=True se variação > 20%."""
    if not historico:
        return False, None
    ultima_carga = historico[0].carga_kg
    if ultima_carga == 0:
        return False, None
    variacao = (carga_nova - ultima_carga) / ultima_carga
    return abs(variacao) > VARIACAO_ANORMAL_PCT, round(variacao * 100, 1)


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------

def registrar(
    user_id: int,
    sessao_data: date,
    posicao: int,
    exercicio_display: str,
    series: int,
    repeticoes: int,
    carga_kg: float,
    db: Session,
) -> RegistroExercicio:
    exercicio_norm = normalizar_nome(exercicio_display)
    rm_result = calcular_rm(carga_kg, repeticoes)
    rm_estimado = rm_result["media"] if rm_result else None

    registro = RegistroExercicio(
        user_id=user_id,
        sessao_data=sessao_data,
        posicao_sessao=posicao,
        exercicio=exercicio_norm,
        exercicio_display=exercicio_display,
        series=series,
        repeticoes=repeticoes,
        carga_kg=carga_kg,
        rm_estimado=rm_estimado,
    )
    db.add(registro)
    db.flush()
    return registro


# ---------------------------------------------------------------------------
# Evolução (para gráficos)
# ---------------------------------------------------------------------------

def get_evolucao_exercicio(
    user_id: int,
    exercicio: str,
    posicao: int | None,
    db: Session,
) -> list[dict]:
    """
    Série temporal de 1RM para um exercício.
    Se `posicao` for informada, filtra apenas sessões onde o exercício
    estava nessa posição (garantindo comparabilidade).
    """
    q = db.query(RegistroExercicio).filter(
        RegistroExercicio.user_id == user_id,
        RegistroExercicio.exercicio == normalizar_nome(exercicio),
        RegistroExercicio.rm_estimado.isnot(None),
    )
    if posicao is not None:
        q = q.filter(RegistroExercicio.posicao_sessao == posicao)

    return [
        {
            "data": r.sessao_data.isoformat(),
            "posicao_sessao": r.posicao_sessao,
            "exercicio_display": r.exercicio_display,
            "series": r.series,
            "repeticoes": r.repeticoes,
            "carga_kg": r.carga_kg,
            "rm_estimado": r.rm_estimado,
        }
        for r in q.order_by(RegistroExercicio.sessao_data).all()
    ]


def get_evolucao_sessao(user_id: int, db: Session) -> list[dict]:
    """
    Soma de 1RMs por sessão — curva de performance geral ao longo do tempo.
    """
    rows = (
        db.query(
            RegistroExercicio.sessao_data,
            func.sum(RegistroExercicio.rm_estimado).label("soma_rm"),
            func.count(RegistroExercicio.id).label("total_exercicios"),
        )
        .filter(
            RegistroExercicio.user_id == user_id,
            RegistroExercicio.rm_estimado.isnot(None),
        )
        .group_by(RegistroExercicio.sessao_data)
        .order_by(RegistroExercicio.sessao_data)
        .all()
    )
    return [
        {
            "data": r.sessao_data.isoformat(),
            "soma_rm": round(r.soma_rm, 1),
            "total_exercicios": r.total_exercicios,
        }
        for r in rows
    ]


def get_historico_recente(user_id: int, db: Session, semanas: int = 4) -> dict:
    """Histórico das execuções das últimas N semanas, agrupado por exercício.
    Para cada exercício: as últimas 3 execuções (mais recentes primeiro).
    Mais a média de 1RM por sessão (para card de evolução)."""
    from datetime import date, timedelta
    limite = date.today() - timedelta(weeks=semanas)
    regs = (
        db.query(RegistroExercicio)
        .filter(RegistroExercicio.user_id == user_id, RegistroExercicio.sessao_data >= limite)
        .order_by(RegistroExercicio.sessao_data.desc(), RegistroExercicio.criado_em.desc())
        .all()
    )
    exercicios: dict[str, list] = {}
    for r in regs:
        nome = r.exercicio_display or r.exercicio
        if nome not in exercicios:
            exercicios[nome] = []
        if len(exercicios[nome]) < 3:
            exercicios[nome].append({
                "data": r.sessao_data.strftime("%d/%m"),
                "series": r.series, "repeticoes": r.repeticoes,
                "carga_kg": r.carga_kg, "rm_estimado": r.rm_estimado,
            })
    from collections import defaultdict
    por_data: dict = defaultdict(list)
    for r in regs:
        if r.rm_estimado is not None:
            por_data[r.sessao_data].append(r.rm_estimado)
    evolucao = [
        {"data": d.strftime("%d/%m"), "media_1rm": round(sum(v) / len(v), 1), "qtd_exercicios": len(v)}
        for d, v in sorted(por_data.items(), reverse=True)
    ]
    return {"exercicios": exercicios, "evolucao_sessoes": evolucao, "periodo_semanas": semanas}
