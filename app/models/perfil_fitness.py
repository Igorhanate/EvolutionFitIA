from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PerfilFitness(Base):
    __tablename__ = "perfis_fitness"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), unique=True, nullable=False)

    # Estaveis - nao reperguntar
    sexo: Mapped[str | None] = mapped_column(String(1), nullable=True)
    data_nascimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    altura_cm: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    # Variaveis - confirmar a cada treino/dieta
    peso_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    nivel_experiencia: Mapped[str | None] = mapped_column(String(20), nullable=True)
    lesoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    objetivo_padrao: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Preferencias de treino
    tipo_treino_padrao: Mapped[str | None] = mapped_column(String(30), nullable=True)
    local_treino_padrao: Mapped[str | None] = mapped_column(String(30), nullable=True)
    horario_treino_padrao: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Especificos de dieta
    restricoes_alimentares: Mapped[str | None] = mapped_column(Text, nullable=True)
    orcamento_alimentar: Mapped[str | None] = mapped_column(String(10), nullable=True)
    tempo_cozinhar: Mapped[str | None] = mapped_column(String(15), nullable=True)

    # Timestamps
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    usuario: Mapped["Usuario"] = relationship(back_populates="perfil_fitness")
