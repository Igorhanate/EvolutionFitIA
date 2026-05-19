from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MetaNutricional(Base):
    __tablename__ = "metas_nutricionais"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    texto_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    calorias_alvo: Mapped[int] = mapped_column(Integer, nullable=False)
    proteinas_alvo_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carboidratos_alvo_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    gorduras_alvo_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    ativa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    usuario: Mapped["Usuario"] = relationship(back_populates="metas_nutricionais")
