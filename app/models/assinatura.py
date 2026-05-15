from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Assinatura(Base):
    __tablename__ = "assinaturas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    plano: Mapped[str] = mapped_column(Enum("trimestral", "anual", name="plano_enum"), nullable=False)
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("ativo", "expirado", "cancelado", name="status_assinatura_enum"),
        default="ativo",
        nullable=False,
    )
    hotmart_transaction_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    usuario: Mapped["Usuario"] = relationship(back_populates="assinaturas")
