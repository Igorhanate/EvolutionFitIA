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
