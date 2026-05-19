from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RegistroRefeicao(Base):
    __tablename__ = "registros_refeicao"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    data_refeicao: Mapped[date] = mapped_column(Date, nullable=False)
    descricao: Mapped[str] = mapped_column(String(500), nullable=False)
    calorias_kcal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    proteinas_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carboidratos_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    gorduras_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    usuario: Mapped["Usuario"] = relationship(back_populates="registros_refeicao")
