from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.foto_composicao import FotoComposicao
from app.models.medida_corporal import MedidaCorporal
from app.models.meta_nutricional import MetaNutricional
from app.models.registro_refeicao import RegistroRefeicao

REMINDER_DAYS = 30
LIMITE_FOTOS_DIA = 6


# ---------------------------------------------------------------------------
# Medidas corporais
# ---------------------------------------------------------------------------

def get_ultima_medida(user_id: int, db: Session) -> MedidaCorporal | None:
    return (
        db.query(MedidaCorporal)
        .filter(MedidaCorporal.user_id == user_id)
        .order_by(MedidaCorporal.data_medicao.desc(), MedidaCorporal.criado_em.desc())
        .first()
    )


def get_historico_medidas(user_id: int, db: Session, limite: int = 10) -> list[MedidaCorporal]:
    return (
        db.query(MedidaCorporal)
        .filter(MedidaCorporal.user_id == user_id)
        .order_by(MedidaCorporal.data_medicao.desc())
        .limit(limite)
        .all()
    )


def needs_measurement_reminder(user_id: int, db: Session) -> bool:
    ultima = get_ultima_medida(user_id, db)
    if not ultima:
        return True
    return (date.today() - ultima.data_medicao).days >= REMINDER_DAYS


def registrar_medidas(user_id: int, data_medicao: date, campos: dict, db: Session) -> MedidaCorporal:
    medida = MedidaCorporal(
        user_id=user_id,
        data_medicao=data_medicao,
        peso_kg=campos.get("peso_kg"),
        cintura_cm=campos.get("cintura_cm"),
        quadril_cm=campos.get("quadril_cm"),
        pescoco_cm=campos.get("pescoco_cm"),
        braco_cm=campos.get("braco_cm"),
        coxa_cm=campos.get("coxa_cm"),
        panturrilha_cm=campos.get("panturrilha_cm"),
    )
    db.add(medida)
    db.flush()
    return medida


# ---------------------------------------------------------------------------
# Fotos de composição
# ---------------------------------------------------------------------------

def get_ultima_foto(user_id: int, db: Session) -> FotoComposicao | None:
    return (
        db.query(FotoComposicao)
        .filter(FotoComposicao.user_id == user_id)
        .order_by(FotoComposicao.criado_em.desc())
        .first()
    )


def registrar_foto_analise(
    user_id: int,
    gordura_pct: float | None,
    analise_texto: str | None,
    db: Session,
) -> FotoComposicao:
    foto = FotoComposicao(
        user_id=user_id,
        gordura_estimada_pct=gordura_pct,
        analise_texto=analise_texto,
    )
    db.add(foto)
    db.flush()
    return foto


# ---------------------------------------------------------------------------
# Refeições
# ---------------------------------------------------------------------------

def get_count_refeicoes_dia(user_id: int, data: date, db: Session) -> int:
    return (
        db.query(func.count(RegistroRefeicao.id))
        .filter(
            RegistroRefeicao.user_id == user_id,
            RegistroRefeicao.data_refeicao == data,
        )
        .scalar()
        or 0
    )


def get_totais_refeicoes_dia(user_id: int, data: date, db: Session) -> dict:
    row = (
        db.query(
            func.coalesce(func.sum(RegistroRefeicao.calorias_kcal), 0).label("calorias"),
            func.coalesce(func.sum(RegistroRefeicao.proteinas_g), 0).label("proteinas"),
            func.coalesce(func.sum(RegistroRefeicao.carboidratos_g), 0).label("carboidratos"),
            func.coalesce(func.sum(RegistroRefeicao.gorduras_g), 0).label("gorduras"),
            func.count(RegistroRefeicao.id).label("total_refeicoes"),
        )
        .filter(
            RegistroRefeicao.user_id == user_id,
            RegistroRefeicao.data_refeicao == data,
        )
        .first()
    )
    return {
        "calorias": int(row.calorias),
        "proteinas": round(float(row.proteinas), 1),
        "carboidratos": round(float(row.carboidratos), 1),
        "gorduras": round(float(row.gorduras), 1),
        "total_refeicoes": int(row.total_refeicoes),
    }


# ---------------------------------------------------------------------------
# Meta nutricional
# ---------------------------------------------------------------------------

def get_meta_ativa(user_id: int, db: Session) -> MetaNutricional | None:
    return (
        db.query(MetaNutricional)
        .filter(MetaNutricional.user_id == user_id, MetaNutricional.ativa.is_(True))
        .order_by(MetaNutricional.criado_em.desc())
        .first()
    )


def cadastrar_meta(
    user_id: int,
    nome: str,
    texto: str | None,
    calorias: int,
    proteinas: float | None,
    carboidratos: float | None,
    gorduras: float | None,
    db: Session,
) -> MetaNutricional:
    db.query(MetaNutricional).filter(
        MetaNutricional.user_id == user_id,
        MetaNutricional.ativa.is_(True),
    ).update({"ativa": False})
    meta = MetaNutricional(
        user_id=user_id,
        nome=nome,
        texto_original=texto,
        calorias_alvo=calorias,
        proteinas_alvo_g=proteinas,
        carboidratos_alvo_g=carboidratos,
        gorduras_alvo_g=gorduras,
        ativa=True,
    )
    db.add(meta)
    db.flush()
    return meta


# ---------------------------------------------------------------------------
# Contexto consolidado para Claude
# ---------------------------------------------------------------------------

def build_nutricao_context(user_id: int, db: Session) -> str | None:
    partes = []
    today = date.today()

    # Última medição corporal
    ultima = get_ultima_medida(user_id, db)
    if ultima:
        campos = []
        if ultima.peso_kg:
            campos.append(f"peso={ultima.peso_kg}kg")
        if ultima.cintura_cm:
            campos.append(f"cintura={ultima.cintura_cm}cm")
        if ultima.quadril_cm:
            campos.append(f"quadril={ultima.quadril_cm}cm")
        if ultima.pescoco_cm:
            campos.append(f"pescoço={ultima.pescoco_cm}cm")
        if ultima.braco_cm:
            campos.append(f"braço={ultima.braco_cm}cm")
        if ultima.coxa_cm:
            campos.append(f"coxa={ultima.coxa_cm}cm")
        if ultima.panturrilha_cm:
            campos.append(f"panturrilha={ultima.panturrilha_cm}cm")
        if campos:
            partes.append(
                f"Última medição corporal ({ultima.data_medicao.strftime('%d/%m/%Y')}): {', '.join(campos)}"
            )
        dias = (today - ultima.data_medicao).days
        if dias >= REMINDER_DAYS:
            partes.append(
                f"[SISTEMA] Última medição há {dias} dias — se pertinente, incentive novas medidas."
            )
    else:
        partes.append(
            "[SISTEMA] Usuário nunca registrou medidas — sugira quando o contexto for adequado."
        )

    # Última análise de foto
    ultima_foto = get_ultima_foto(user_id, db)
    if ultima_foto:
        foto_str = f"Última análise de composição corporal ({ultima_foto.criado_em.strftime('%d/%m/%Y')})"
        if ultima_foto.gordura_estimada_pct:
            foto_str += f": ~{ultima_foto.gordura_estimada_pct}% de gordura estimado"
        partes.append(foto_str)

    # Refeições do dia
    totais = get_totais_refeicoes_dia(user_id, today, db)
    if totais["total_refeicoes"] > 0:
        partes.append(
            f"Refeições registradas hoje ({totais['total_refeicoes']}): "
            f"{totais['calorias']} kcal | P:{totais['proteinas']}g C:{totais['carboidratos']}g G:{totais['gorduras']}g"
        )

    # Meta nutricional ativa
    meta = get_meta_ativa(user_id, db)
    if meta:
        meta_str = f"Meta nutricional ativa: '{meta.nome}' — {meta.calorias_alvo} kcal/dia"
        macros = []
        if meta.proteinas_alvo_g:
            macros.append(f"P:{meta.proteinas_alvo_g}g")
        if meta.carboidratos_alvo_g:
            macros.append(f"C:{meta.carboidratos_alvo_g}g")
        if meta.gorduras_alvo_g:
            macros.append(f"G:{meta.gorduras_alvo_g}g")
        if macros:
            meta_str += f" | {' '.join(macros)}"
        partes.append(meta_str)

    return "\n".join(partes) if partes else None
