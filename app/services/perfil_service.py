from sqlalchemy.orm import Session

from app.models.perfil_fitness import PerfilFitness

CAMPOS_OBRIGATORIOS_PERFIL = ("sexo", "data_nascimento", "altura_cm", "peso_kg", "nivel_experiencia")


def get_or_create_perfil(user_id: int, db: Session) -> PerfilFitness:
    perfil = db.query(PerfilFitness).filter(PerfilFitness.user_id == user_id).first()
    if not perfil:
        perfil = PerfilFitness(user_id=user_id)
        db.add(perfil)
        db.flush()
    return perfil


def perfil_minimo_completo(perfil: PerfilFitness) -> bool:
    return all(getattr(perfil, c, None) is not None for c in CAMPOS_OBRIGATORIOS_PERFIL)


def calcular_idade(data_nasc) -> int | None:
    if not data_nasc:
        return None
    from datetime import date
    hoje = date.today()
    return hoje.year - data_nasc.year - ((hoje.month, hoje.day) < (data_nasc.month, data_nasc.day))


def faltam_medidas_ou_fotos(user_id: int, db: Session) -> dict:
    from app.models.medida_corporal import MedidaCorporal
    from app.models.foto_composicao import FotoComposicao
    medidas = db.query(MedidaCorporal).filter(MedidaCorporal.user_id == user_id).first() is None
    fotos = db.query(FotoComposicao).filter(FotoComposicao.user_id == user_id).first() is None
    return {"medidas": medidas, "fotos": fotos}


def atualizar_peso_perfil(user_id: int, peso_kg: float, db: Session) -> dict:
    """Atualiza PerfilFitness.peso_kg. Retorna {"anterior": float|None, "novo": float, "diff": float|None}."""
    perfil = get_or_create_perfil(user_id, db)
    anterior = float(perfil.peso_kg) if perfil.peso_kg is not None else None
    perfil.peso_kg = peso_kg
    db.flush()
    diff = abs(peso_kg - anterior) if anterior is not None else None
    return {"anterior": anterior, "novo": peso_kg, "diff": diff}


def atualizar_nivel_perfil(user_id: int, nivel: str, db: Session) -> dict:
    """Atualiza PerfilFitness.nivel_experiencia. nivel deve ser 'iniciante', 'intermediario' ou 'avancado'."""
    valido = {"iniciante", "intermediario", "avancado"}
    if nivel not in valido:
        return {"erro": f"nivel invalido: {nivel}"}
    perfil = get_or_create_perfil(user_id, db)
    anterior = perfil.nivel_experiencia
    perfil.nivel_experiencia = nivel
    db.flush()
    return {"anterior": anterior, "novo": nivel}
