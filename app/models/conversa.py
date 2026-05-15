from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Conversa(Base):
    __tablename__ = "conversas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=False, unique=True)
    mensagens: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    usuario: Mapped["Usuario"] = relationship(back_populates="conversa")
