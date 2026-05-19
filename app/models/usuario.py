from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telefone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    nome: Mapped[str | None] = mapped_column(String(150), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ultima_mensagem_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    assinaturas: Mapped[list["Assinatura"]] = relationship(back_populates="usuario")
    treinos: Mapped[list["Treino"]] = relationship(back_populates="usuario")
    dietas: Mapped[list["Dieta"]] = relationship(back_populates="usuario")
    conversa: Mapped["Conversa | None"] = relationship(back_populates="usuario", uselist=False)
