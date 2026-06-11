from datetime import datetime, date
from sqlalchemy import String, Date, DateTime, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from agente_insta.db import Base


class PostGerado(Base):
    __tablename__ = "posts_gerados"

    id: Mapped[int] = mapped_column(primary_key=True)
    data_geracao: Mapped[date] = mapped_column(Date, index=True)
    categoria: Mapped[str] = mapped_column(String(40))
    formato: Mapped[str] = mapped_column(String(20))
    tema: Mapped[str] = mapped_column(Text)
    conteudo: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default="novo")
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
