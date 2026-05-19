from datetime import date

from sqlalchemy.orm import Session

from app.models.foto_composicao import FotoComposicao
from app.models.medida_corporal import MedidaCorporal

REMINDER_DAYS = 30


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


def build_nutricao_context(user_id: int, db: Session) -> str | None:
    partes = []

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

        dias = (date.today() - ultima.data_medicao).days
        if dias >= REMINDER_DAYS:
            partes.append(
                f"[SISTEMA] Última medição há {dias} dias — se o contexto for apropriado, "
                "incentive o usuário a registrar novas medidas."
            )
    else:
        partes.append(
            "[SISTEMA] Usuário nunca registrou medidas corporais — se o contexto for "
            "relacionado a dieta, treino ou evolução, sugira registrar peso e medidas."
        )

    ultima_foto = get_ultima_foto(user_id, db)
    if ultima_foto:
        foto_str = f"Última análise de composição corporal ({ultima_foto.criado_em.strftime('%d/%m/%Y')})"
        if ultima_foto.gordura_estimada_pct:
            foto_str += f": ~{ultima_foto.gordura_estimada_pct}% de gordura estimado"
        partes.append(foto_str)

    return "\n".join(partes) if partes else None
