from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MensagemProcessada(Base):
    __tablename__ = "mensagens_processadas"

    message_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    recebido_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    usuario: Mapped["Usuario | None"] = relationship()
