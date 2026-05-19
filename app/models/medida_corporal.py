from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MedidaCorporal(Base):
    __tablename__ = "medidas_corporais"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    data_medicao: Mapped[date] = mapped_column(Date, nullable=False)
    peso_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    cintura_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    quadril_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    pescoco_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    braco_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    coxa_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    panturrilha_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    usuario: Mapped["Usuario"] = relationship(back_populates="medidas_corporais")
