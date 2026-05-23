from sqlalchemy.orm import Session

from app.models.perfil_fitness import PerfilFitness


def get_or_create_perfil(user_id: int, db: Session) -> PerfilFitness:
    perfil = db.query(PerfilFitness).filter(PerfilFitness.user_id == user_id).first()
    if not perfil:
        perfil = PerfilFitness(user_id=user_id)
        db.add(perfil)
        db.flush()
    return perfil
