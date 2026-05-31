from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class SessaoTreino(Base):
    __tablename__ = "sessoes_treino"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    treino_nome: Mapped[str] = mapped_column(String(100), nullable=False)
    iniciada_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    finalizada_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
