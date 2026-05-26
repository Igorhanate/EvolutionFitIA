from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AlimentoTACO(Base):
    __tablename__ = "alimentos_taco"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    taco_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    categoria: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    kcal: Mapped[float | None] = mapped_column(Float, nullable=True)
    proteina_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    lipideos_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carboidrato_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fibra_g: Mapped[float | None] = mapped_column(Float, nullable=True)
