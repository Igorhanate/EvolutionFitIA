from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LembreteRemedio(Base):
    __tablename__ = "lembretes_remedio"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    nome_norm: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    quantidade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    intervalo_horas: Mapped[int] = mapped_column(Integer, nullable=False)
    proximo_em: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    fim_em: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    terminado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    usuario: Mapped["Usuario"] = relationship(back_populates="lembretes_remedio")
