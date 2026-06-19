from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PerfilTreinoModalidade(Base):
    """Perfil de treino completo e independente por modalidade (musculacao, yoga, corrida...).

    Uma linha por (user_id + modalidade). Os 7 campos sao independentes entre modalidades.
    O PerfilFitness continua existindo (identidade + perfil geral); esta tabela e ADITIVA.
    """
    __tablename__ = "perfil_treino_modalidade"
    __table_args__ = (UniqueConstraint("user_id", "modalidade", name="uq_perfil_treino_user_modalidade"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    modalidade: Mapped[str] = mapped_column(String(30), nullable=False)

    local: Mapped[str | None] = mapped_column(String(30), nullable=True)
    objetivo: Mapped[str | None] = mapped_column(String(30), nullable=True)
    dias_semana: Mapped[str | None] = mapped_column(String(10), nullable=True)
    tempo_sessao: Mapped[str | None] = mapped_column(String(20), nullable=True)
    nivel: Mapped[str | None] = mapped_column(String(20), nullable=True)
    lesoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    horario: Mapped[str | None] = mapped_column(String(20), nullable=True)

    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    usuario: Mapped["Usuario"] = relationship(back_populates="perfis_treino_modalidade")
