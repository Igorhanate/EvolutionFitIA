from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PerfilHabitos(Base):
    __tablename__ = "perfis_habitos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), unique=True, nullable=False)
    suplementos: Mapped[list | None] = mapped_column(JSON, nullable=True)
    streak_inicio_sem_fumar: Mapped[date | None] = mapped_column(Date, nullable=True)
    streak_inicio_sem_alcool: Mapped[date | None] = mapped_column(Date, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    usuario: Mapped["Usuario"] = relationship(back_populates="perfil_habitos")
