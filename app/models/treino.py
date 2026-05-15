from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Treino(Base):
    __tablename__ = "treinos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    conteudo: Mapped[dict] = mapped_column(JSON, nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    usuario: Mapped["Usuario"] = relationship(back_populates="treinos")
