from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class HabitoDia(Base):
    __tablename__ = "habitos_dia"
    __table_args__ = (UniqueConstraint("user_id", "data", name="uq_habito_dia_user_data"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False, index=True)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    agua_ml: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    fumou: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    bebeu_alcool: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    suplementos_tomados: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    usuario: Mapped["Usuario"] = relationship(back_populates="habitos_dia")
