from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RegistroExercicio(Base):
    __tablename__ = "registros_exercicio"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    sessao_data: Mapped[date] = mapped_column(Date, nullable=False)
    posicao_sessao: Mapped[int] = mapped_column(Integer, nullable=False)
    exercicio: Mapped[str] = mapped_column(String(200), nullable=False)        # normalizado (lowercase)
    exercicio_display: Mapped[str] = mapped_column(String(200), nullable=False) # original do usuário
    series: Mapped[int] = mapped_column(Integer, nullable=False)
    repeticoes: Mapped[int] = mapped_column(Integer, nullable=False)
    carga_kg: Mapped[float] = mapped_column(Float, nullable=False)
    rm_estimado: Mapped[float | None] = mapped_column(Float, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    usuario: Mapped["Usuario"] = relationship(back_populates="registros_exercicio")
